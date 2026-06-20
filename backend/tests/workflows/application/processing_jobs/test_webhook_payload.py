from uuid import uuid4

from expects import be_none, equal, expect, have_key

from src.common.domain.enums.webhooks import WebhookEventType
from src.common.domain.enums.workflows import WorkflowDocumentStatus
from src.common.domain.models.processing.workflow import Workflow
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.workflows.application.processing_jobs.webhook_payload import (
    build_event_payload,
    build_extraction_payload,
)

# --- build_extraction_payload (confidence derivation, §4.4) ---


def test_build_extraction_payload__uses_min_non_null_bbox_confidence():
    mapped = {"total": {"value": 10, "bbox": [{"confidence": 0.9}, {"confidence": 0.7}, {"confidence": None}]}}

    result = build_extraction_payload(mapped, {})

    expect(result["total"]["value"]).to(equal(10))
    expect(result["total"]["confidence"]).to(equal(0.7))


def test_build_extraction_payload__inferred_field_has_no_confidence():
    mapped = {"x": {"value": "a", "inferred": True, "bbox": [{"confidence": 0.9}]}}

    result = build_extraction_payload(mapped, {})

    expect(result["x"]["confidence"]).to(be_none)


def test_build_extraction_payload__no_bbox_means_none_confidence():
    result = build_extraction_payload({"x": {"value": "a", "bbox": []}}, {})

    expect(result["x"]["confidence"]).to(be_none)


def test_build_extraction_payload__falls_back_to_raw_when_mapped_none():
    result = build_extraction_payload(None, {"due_date": "2026-01-01"})

    expect(result["due_date"]).to(equal({"value": "2026-01-01", "confidence": None}))


def test_build_extraction_payload__returns_none_when_nothing_extracted():
    expect(build_extraction_payload(None, None)).to(be_none)
    expect(build_extraction_payload(None, {})).to(be_none)


# --- build_event_payload (envelope, §4.3) ---


def _workflow() -> Workflow:
    return Workflow(uuid=uuid4(), tenant_id=uuid4(), name="Facturación")


def _processing_job() -> WorkflowProcessingJob:
    return WorkflowProcessingJob(
        uuid=uuid4(),
        temporal_workflow_id="run-1",
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        file_id=uuid4(),
    )


def _document(status: WorkflowDocumentStatus, **kwargs) -> WorkflowDocument:
    return WorkflowDocument(uuid=uuid4(), tenant_id=uuid4(), status=status, **kwargs)


def test_build_event_payload__uses_camel_case_envelope():
    payload = build_event_payload(
        workflow=_workflow(),
        processing_job=_processing_job(),
        document=_document(WorkflowDocumentStatus.EXTRACTED),
        document_type_name="Factura",
        event_type=WebhookEventType.DOCUMENT_EXTRACTED,
        event_id="evt_1",
        final_status="COMPLETED",
    )

    expect(payload).to(have_key("eventId"))
    expect(payload).to(have_key("occurredAt"))
    expect(payload).to(have_key("processingJob"))
    expect(payload["event"]).to(equal("document.extracted"))


def test_build_event_payload__preserves_extraction_field_names():
    payload = build_event_payload(
        workflow=_workflow(),
        processing_job=_processing_job(),
        document=_document(
            WorkflowDocumentStatus.EXTRACTED,
            mapped_extraction={"due_date": {"value": 1, "bbox": []}},
        ),
        document_type_name=None,
        event_type=WebhookEventType.DOCUMENT_EXTRACTED,
        event_id="evt_1",
        final_status="COMPLETED",
    )

    # The document's own field name must NOT be camelCased to "dueDate".
    expect(payload["document"]["extraction"]).to(have_key("due_date"))


def test_build_event_payload__webhook_projection_filters_extraction_fields():
    # phases-config · finalize.webhook_projection: solo los campos pedidos viajan.
    payload = build_event_payload(
        workflow=_workflow(),
        processing_job=_processing_job(),
        document=_document(
            WorkflowDocumentStatus.EXTRACTED,
            mapped_extraction={"due_date": {"value": 1, "bbox": []}, "amount": {"value": 9, "bbox": []}},
        ),
        document_type_name=None,
        event_type=WebhookEventType.DOCUMENT_EXTRACTED,
        event_id="evt_1",
        final_status="COMPLETED",
        field_projection=["due_date"],
    )

    extraction = payload["document"]["extraction"]
    expect(extraction).to(have_key("due_date"))
    expect(extraction).not_to(have_key("amount"))


def test_build_event_payload__failed_includes_error():
    payload = build_event_payload(
        workflow=_workflow(),
        processing_job=_processing_job(),
        document=_document(
            WorkflowDocumentStatus.ERROR,
            error={"code": "EXTRACTION_FAILED", "message": "boom"},
        ),
        document_type_name=None,
        event_type=WebhookEventType.DOCUMENT_FAILED,
        event_id="evt_2",
        final_status="FAILED",
    )

    expect(payload["event"]).to(equal("document.failed"))
    expect(payload["document"]["error"]).to(have_key("code"))


def test_build_event_payload__omits_oversized_plain_text():
    big_text = "x" * (5 * 1024 * 1024 + 1)

    payload = build_event_payload(
        workflow=_workflow(),
        processing_job=_processing_job(),
        document=_document(WorkflowDocumentStatus.EXTRACTED, extracted_text=big_text),
        document_type_name=None,
        event_type=WebhookEventType.DOCUMENT_EXTRACTED,
        event_id="evt_3",
        final_status="COMPLETED",
    )

    expect(payload["document"]["plainText"]).to(be_none)
    expect(payload["document"]["plainTextOmitted"]).to(equal(True))
