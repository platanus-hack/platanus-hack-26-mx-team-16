"""E3 · activity `assess_document`: S3 + LLM mockeados, persistencia real.

Verifica que la activity descarga el artefacto extract_text, slicea por
page_range, llama al agente y persiste `extract_confidence` + `signals` con
MERGE (sin duplicar) de `needs_clarification`. Un payload LLM malformado
deja el documento sin assess (label-only, sin excepción).
"""

from __future__ import annotations

import io
import json
from uuid import uuid4

import pytest
from expects import be_false, be_none, be_true, contain, equal, expect

from src.common.database.config import get_database_config
from src.common.database.models.workflow_document import WorkflowDocumentORM
from src.workflows.infrastructure.services.assess.agent import AssessAgent
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    StaticLLMRunner,
)
from src.workflows.presentation.workflows.activities.assess_document import (
    AssessDocumentActivity,
)
from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    AssessDocumentInput,
)

_EXTRACT_TEXT_JSON = {
    "status": "ok",
    "layouts": {
        "pages": [
            {"page_number": 1, "formatted_text": "RUT: 12.345.678-9"},
            {"page_number": 2, "formatted_text": "Nombre: Juan Pérez / Pedro Pérez"},
            {"page_number": 3, "formatted_text": "Otra página fuera de rango"},
        ]
    },
}


class FakeS3Client:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.calls: list[tuple[str, str]] = []

    def get_object(self, Bucket: str, Key: str) -> dict:  # noqa: N803
        self.calls.append((Bucket, Key))
        return {"Body": io.BytesIO(json.dumps(self._payload).encode("utf-8"))}


@pytest.fixture
async def document_orm(async_session, tenant_orm, workflow_orm):
    doc = WorkflowDocumentORM(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        name="Cédula",
        needs_clarification=["campo_previo"],
    )
    async_session.add(doc)
    await async_session.commit()
    return doc


def _activity(llm_payload: dict, s3_client: FakeS3Client) -> AssessDocumentActivity:
    return AssessDocumentActivity(
        session_maker=get_database_config().session_maker,
        assess_agent=AssessAgent(llm_runner=StaticLLMRunner(payload=llm_payload)),
        boto3_client=s3_client,
    )


def _input(document_orm) -> AssessDocumentInput:
    return AssessDocumentInput(
        document_id=document_orm.uuid,
        tenant_id=document_orm.tenant_id,
        extract_text_source="s3://bucket/jobs/j1/extract_text.json",
        page_range={"from": 1, "to": 2},
        document_type_name="Cédula",
        fields={"rut": "12.345.678-9", "nombre": "Juan Pérez"},
    )


async def test_assess_document__persists_columns_and_merges_needs_clarification(async_session, document_orm):
    s3 = FakeS3Client(_EXTRACT_TEXT_JSON)
    activity = _activity(
        {
            "fields": {
                "rut": {"extract_confidence": 0.95},
                "nombre": {
                    "extract_confidence": 0.4,
                    "signals": ["multiple_possible_answers"],
                    "explanation": "Hay dos nombres plausibles en el documento.",
                    "candidates": ["Juan Pérez", "Pedro Pérez"],
                },
            }
        },
        s3,
    )

    output = await activity.assess_document(_input(document_orm))

    expect(output.assessed).to(be_true)
    expect(output.fields_assessed).to(equal(2))
    expect(output.flagged).to(equal(["nombre"]))
    expect(s3.calls).to(equal([("bucket", "jobs/j1/extract_text.json")]))

    await async_session.refresh(document_orm)
    expect(document_orm.extract_confidence).to(equal({"rut": 0.95, "nombre": 0.4}))
    expect(document_orm.signals).to(
        equal(
            {
                "nombre": {
                    "signals": ["multiple_possible_answers"],
                    "explanation": "Hay dos nombres plausibles en el documento.",
                    "candidates": ["Juan Pérez", "Pedro Pérez"],
                }
            }
        )
    )
    # merge sin duplicar: lo previo se conserva, lo nuevo se añade
    expect(document_orm.needs_clarification).to(equal(["campo_previo", "nombre"]))


async def test_assess_document__min_confidence_flags_low_fields(async_session, document_orm):
    # phases-config · assess.min_confidence: sin signals, los campos por debajo
    # del umbral se marcan needs_clarification igual.
    s3 = FakeS3Client(_EXTRACT_TEXT_JSON)
    activity = _activity(
        {"fields": {"rut": {"extract_confidence": 0.95}, "nombre": {"extract_confidence": 0.4}}},
        s3,
    )
    payload = _input(document_orm).model_copy(update={"min_confidence": 0.6})

    output = await activity.assess_document(payload)

    expect(output.flagged).to(contain("nombre"))  # 0.4 < 0.6
    expect(output.flagged).not_to(contain("rut"))  # 0.95 ≥ 0.6
    await async_session.refresh(document_orm)
    expect(document_orm.needs_clarification).to(contain("nombre"))


async def test_assess_document__malformed_llm_payload_leaves_document_untouched(async_session, document_orm):
    activity = _activity({"unexpected": "shape"}, FakeS3Client(_EXTRACT_TEXT_JSON))

    output = await activity.assess_document(_input(document_orm))

    expect(output.assessed).to(be_false)
    expect(output.fields_assessed).to(equal(0))

    await async_session.refresh(document_orm)
    expect(document_orm.extract_confidence).to(be_none)
    expect(document_orm.signals).to(be_none)
    expect(document_orm.needs_clarification).to(equal(["campo_previo"]))


async def test_assess_document__no_fields_short_circuits_without_s3(document_orm):
    s3 = FakeS3Client(_EXTRACT_TEXT_JSON)
    activity = _activity({"fields": {}}, s3)
    payload = _input(document_orm).model_copy(update={"fields": {}})

    output = await activity.assess_document(payload)

    expect(output.assessed).to(be_false)
    expect(s3.calls).to(equal([]))


async def test_assess_document__empty_text_slice_skips_assessment(async_session, document_orm):
    # page_range fuera de las páginas del artefacto ⇒ slice vacío ⇒ sin assess
    activity = _activity(
        {"fields": {"rut": {"extract_confidence": 1.0}}},
        FakeS3Client({"layouts": {"pages": []}}),
    )

    output = await activity.assess_document(_input(document_orm))

    expect(output.assessed).to(be_false)
    await async_session.refresh(document_orm)
    expect(document_orm.extract_confidence).to(be_none)
