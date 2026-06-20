"""E4 · `split_classified_documents` — parte un classify_pages en slices S3.

La activity lee el output de classify_pages, escribe UN JSON por documento
(`{"documents": [doc]}` — el shape que `_resolve_documents` de la Lambda
extract_fields resuelve vía ``source_uri``) y devuelve refs compactas
``{document_index, source_uri}``. Claves deterministas
(``classify_pages.doc_NNN.json``) para que los retries sobreescriban el mismo
objeto.
"""

from __future__ import annotations

import json
from io import BytesIO

from expects import equal, expect, have_length

from src.common.domain.entities.workflows.document_processing import ReadS3JsonInput
from src.workflows.presentation.workflows.activities.read_s3_json import (
    ReadS3JsonActivity,
    per_document_classify_key,
)


class _StubS3Client:
    def __init__(self, body: dict):
        self._body = json.dumps(body).encode("utf-8")
        self.puts: list[dict] = []

    def get_object(self, Bucket: str, Key: str) -> dict:
        return {"Body": BytesIO(self._body)}

    def put_object(self, **kwargs) -> None:
        self.puts.append(kwargs)


def _classify_body() -> dict:
    return {
        "status": "success",
        "classification": {
            "documents": [
                {
                    "document_index": 0,
                    "document_type": {"uuid": "aaa", "name": "Cedula", "fields": {}},
                    "pages": [{"page_number": 1, "text": "LAURA"}],
                },
                {
                    "document_index": 1,
                    "document_type": {"uuid": "aaa", "name": "Cedula", "fields": {}},
                    "pages": [{"page_number": 2, "text": "PEDRO"}],
                },
            ]
        },
    }


def test_per_document_classify_key__derives_deterministic_sibling_keys():
    expect(per_document_classify_key("jobs/run/classify_pages.json", 0)).to(
        equal("jobs/run/classify_pages.doc_000.json")
    )
    expect(per_document_classify_key("jobs/run/classify_pages.json", 12)).to(
        equal("jobs/run/classify_pages.doc_012.json")
    )
    # Sin extensión .json: sufijo igualmente determinista
    expect(per_document_classify_key("jobs/run/classify_pages", 1)).to(
        equal("jobs/run/classify_pages.doc_001.json")
    )


async def test_split__writes_one_slice_per_document_and_returns_refs():
    # Arrange
    client = _StubS3Client(_classify_body())
    activity = ReadS3JsonActivity(boto3_client=client)

    # Act
    output = await activity.split_classified_documents(
        ReadS3JsonInput(source="s3://bucket/jobs/run/classify_pages.json")
    )

    # Assert — refs compactas, una por doc, con la clave derivada
    expect(output.documents).to(have_length(2))
    expect([d.document_index for d in output.documents]).to(equal([0, 1]))
    expect([d.source_uri for d in output.documents]).to(
        equal(
            [
                "s3://bucket/jobs/run/classify_pages.doc_000.json",
                "s3://bucket/jobs/run/classify_pages.doc_001.json",
            ]
        )
    )
    # Cada slice es {"documents": [doc]} — lo que la Lambda resuelve por source_uri
    expect(client.puts).to(have_length(2))
    for put, expected_text in zip(client.puts, ["LAURA", "PEDRO"]):
        body = json.loads(put["Body"])
        expect(sorted(body)).to(equal(["documents"]))
        expect(body["documents"]).to(have_length(1))
        expect(body["documents"][0]["pages"][0]["text"]).to(equal(expected_text))
    expect([p["Key"] for p in client.puts]).to(
        equal(["jobs/run/classify_pages.doc_000.json", "jobs/run/classify_pages.doc_001.json"])
    )


async def test_split__honors_embedded_document_index_like_extract_classified_refs():
    # Arrange — entries con document_index propio NO consecutivo: el slice se
    # archiva bajo ese índice (mismo criterio que extract_classified_refs,
    # para que siempre cuadre con los persisted_docs del run).
    body = _classify_body()
    body["classification"]["documents"][1]["document_index"] = 7
    client = _StubS3Client(body)
    activity = ReadS3JsonActivity(boto3_client=client)

    # Act
    output = await activity.split_classified_documents(
        ReadS3JsonInput(source="s3://bucket/jobs/run/classify_pages.json")
    )

    # Assert
    expect([d.document_index for d in output.documents]).to(equal([0, 7]))
    expect(output.documents[1].source_uri).to(
        equal("s3://bucket/jobs/run/classify_pages.doc_007.json")
    )


async def test_split__unwrapped_payload_falls_back_to_root_documents():
    # Arrange — payload sin wrapper "classification" (mismo fallback que
    # read_classified_refs y que la propia Lambda)
    body = {"documents": _classify_body()["classification"]["documents"]}
    client = _StubS3Client(body)
    activity = ReadS3JsonActivity(boto3_client=client)

    # Act
    output = await activity.split_classified_documents(
        ReadS3JsonInput(source="s3://bucket/jobs/run/classify_pages.json")
    )

    # Assert
    expect(output.documents).to(have_length(2))
