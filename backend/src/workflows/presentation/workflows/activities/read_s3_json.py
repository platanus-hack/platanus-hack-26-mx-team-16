"""Activities that download JSON objects from S3 for the document pipeline.

The boto3 S3 client is sync; the I/O is offloaded to a worker thread via
`asyncio.to_thread` so the activity does not block the worker's event
loop while pulling potentially large JSON outputs (classify_pages,
extract_text).

`read_s3_json` returns the parsed JSON verbatim — only safe for payloads
known to stay under Temporal's 2 MiB result limit. For the classify_pages
output (which embeds full per-page text + layout blocks and easily exceeds
the limit on large files — TMPRL1103) use `read_classified_refs`, which
parses in-activity and returns only the compact document refs.
"""

from __future__ import annotations

import asyncio
import json

import boto3
from botocore.client import BaseClient
from temporalio import activity

from src.common.domain.entities.workflows.document_processing import ReadS3JsonInput
from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    ReadClassifiedRefsOutput,
    SplitClassifiedDocumentsOutput,
    SplitDocumentRef,
)


def split_s3_uri(source: str) -> tuple[str, str]:
    """Split an `s3://bucket/key` URI into `(bucket, key)`."""
    if not source.startswith("s3://"):
        raise ValueError(f"Invalid S3 source: {source}")
    without_scheme = source[len("s3://") :]
    bucket, _, key = without_scheme.partition("/")
    return bucket, key


def per_document_classify_key(key: str, document_index: int) -> str:
    """Deterministic S3 key for the per-document slice of a classify output.

    ``jobs/.../classify_pages.json`` → ``jobs/.../classify_pages.doc_000.json``.
    Deterministic so activity retries overwrite the same object (idempotent).
    """
    base = key[: -len(".json")] if key.endswith(".json") else key
    return f"{base}.doc_{document_index:03d}.json"


class ReadS3JsonActivity:
    def __init__(self, boto3_client: BaseClient | None = None) -> None:
        self._client = boto3_client or boto3.client("s3")

    @activity.defn(name="read_s3_json")
    async def read_s3_json(self, input: ReadS3JsonInput) -> dict:
        data = ReadS3JsonInput.model_validate(input)
        bucket, key = split_s3_uri(data.source)

        body_bytes = await asyncio.to_thread(self._fetch_blocking, bucket, key)
        return json.loads(body_bytes)

    @activity.defn(name="read_classified_refs")
    async def read_classified_refs(self, input: ReadS3JsonInput) -> ReadClassifiedRefsOutput:
        """Read a classify_pages output and return only the compact refs."""
        from src.workflows.presentation.workflows.payload_helpers import (
            extract_classified_refs,
        )

        data = ReadS3JsonInput.model_validate(input)
        bucket, key = split_s3_uri(data.source)

        body_bytes = await asyncio.to_thread(self._fetch_blocking, bucket, key)
        classify_data = json.loads(body_bytes)

        classification = classify_data.get("classification") or classify_data
        raw_docs = classification.get("documents") or []
        return ReadClassifiedRefsOutput(
            documents=extract_classified_refs(classify_data),
            total_raw=len(raw_docs),
        )

    @activity.defn(name="split_classified_documents")
    async def split_classified_documents(self, input: ReadS3JsonInput) -> SplitClassifiedDocumentsOutput:
        """Split a classify_pages output into one S3 JSON per classified document (E4).

        Each slice is ``{"documents": [doc]}`` — the exact shape the
        extract_fields Lambda resolves via ``source_uri`` (it falls back to the
        root when there is no ``classification`` wrapper), so the Lambda can be
        invoked once per document with the same payload contract as today.
        ``document_index`` mirrors ``extract_classified_refs`` (the entry's own
        index when present, else its array position) so the refs the workflow
        persisted and the slices returned here always line up.
        """
        data = ReadS3JsonInput.model_validate(input)
        bucket, key = split_s3_uri(data.source)

        body_bytes = await asyncio.to_thread(self._fetch_blocking, bucket, key)
        classify_data = json.loads(body_bytes)
        classification = classify_data.get("classification") or classify_data
        raw_docs = classification.get("documents") or []

        refs: list[SplitDocumentRef] = []
        for position, entry in enumerate(raw_docs):
            if not isinstance(entry, dict):
                continue
            index = int(entry.get("document_index", position))
            doc_key = per_document_classify_key(key, index)
            payload = json.dumps({"documents": [entry]}).encode("utf-8")
            await asyncio.to_thread(self._put_blocking, bucket, doc_key, payload)
            refs.append(SplitDocumentRef(document_index=index, source_uri=f"s3://{bucket}/{doc_key}"))
        return SplitClassifiedDocumentsOutput(documents=refs)

    def _fetch_blocking(self, bucket: str, key: str) -> bytes:
        response = self._client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()

    def _put_blocking(self, bucket: str, key: str, body: bytes) -> None:
        self._client.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")
