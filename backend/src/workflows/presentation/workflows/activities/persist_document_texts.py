"""Activity that slices the OCR text per document and persists it directly.

The extract_text S3 output (layout JSON with per-page text + blocks) easily
exceeds Temporal's 2 MiB payload limit on large files (TMPRL1103), and the
sliced plain text of a big document can too. So neither may travel through
workflow history: this activity reads the JSON from S3, slices each
document's page range, and UPDATEs `workflow_documents.extracted_text`
in-place. The workflow only ships the compact `{document_id, page_range}`
refs in and gets a row count back.
"""

from __future__ import annotations

import asyncio
import json

import boto3
from botocore.client import BaseClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio import activity

from src.common.application.logging import get_logger
from src.common.database.models.workflow_document import WorkflowDocumentORM
from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    PersistDocumentTextsInput,
)
from src.workflows.presentation.workflows.activities.read_s3_json import split_s3_uri

logger = get_logger(__name__)


class PersistDocumentTextsActivity:
    def __init__(
        self,
        session_maker: async_sessionmaker,
        boto3_client: BaseClient | None = None,
    ) -> None:
        self._session_maker = session_maker
        self._client = boto3_client or boto3.client("s3")

    @activity.defn(name="persist_document_texts")
    async def persist_document_texts(self, payload: PersistDocumentTextsInput) -> int:
        from src.workflows.presentation.workflows.payload_helpers import (
            build_page_text_map,
            slice_document_text,
        )

        data = PersistDocumentTextsInput.model_validate(payload)
        bucket, key = split_s3_uri(data.source)

        body_bytes = await asyncio.to_thread(self._fetch_blocking, bucket, key)
        page_text_map = build_page_text_map(json.loads(body_bytes))

        updated = 0
        async with self._session_maker() as session:
            for doc in data.documents:
                text = slice_document_text(page_text_map, doc.page_range)
                if not text:
                    continue
                await session.execute(
                    update(WorkflowDocumentORM)
                    .where(WorkflowDocumentORM.uuid == doc.document_id)
                    .values(extracted_text=text)
                )
                updated += 1
            await session.commit()

        logger.info(
            f"persist_document_texts.done source={data.source} "
            f"documents={len(data.documents)} updated={updated}"
        )
        return updated

    def _fetch_blocking(self, bucket: str, key: str) -> bytes:
        response = self._client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()
