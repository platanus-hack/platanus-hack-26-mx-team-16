"""Builders for the outbound webhook payload (spec §4.3 / §4.4).

The payload is built with snake_case keys and then run through
``convert_to_camel_case`` so the wire contract is camelCase. ``extraction`` is
wrapped in ``RawJson`` so the document's own field names are preserved verbatim.
"""

from __future__ import annotations

from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.application.helpers.json_encoder import RawJson, convert_to_camel_case
from src.common.domain.enums.webhooks import WebhookEventType
from src.common.domain.models.processing.workflow import Workflow
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.workflows.domain.services.field_confidence import compute_field_confidence

# §6 size guard: omit plainText above this body-size proxy (bytes of OCR text).
PLAIN_TEXT_MAX_BYTES = 5 * 1024 * 1024


def build_extraction_payload(
    mapped_extraction: dict | None,
    extraction: dict | None,
) -> dict | None:
    """Per-field ``{value, confidence}`` (§4.4), or ``None`` if nothing extracted.

    Reuses the shared :func:`compute_field_confidence` (F4) so the payload reflects
    the same per-field scores persisted on the document; ``source`` is projected
    away to keep the §4.4 wire contract (``{value, confidence}``).
    """
    field_confidence = compute_field_confidence(mapped_extraction, extraction)
    if not field_confidence:
        return None
    return {
        field: {"value": entry["value"], "confidence": entry["confidence"]}
        for field, entry in field_confidence.items()
    }


def build_event_payload(
    *,
    workflow: Workflow,
    processing_job: WorkflowProcessingJob,
    document: WorkflowDocument,
    document_type_name: str | None,
    event_type: WebhookEventType,
    event_id: str,
    final_status: str,
    field_projection: list[str] | None = None,
) -> dict[str, Any]:
    """Build the immutable camelCase payload snapshot for one document (§4.3)."""
    extraction_payload = build_extraction_payload(document.mapped_extraction, document.extraction)
    # phases-config · finalize.webhook_projection: recorta el `extraction` al
    # subconjunto de campos pedido. None ⇒ todos (comportamiento de hoy).
    if field_projection is not None and extraction_payload:
        allow = set(field_projection)
        extraction_payload = {k: v for k, v in extraction_payload.items() if k in allow}

    document_type = None
    if document.document_type_id is not None:
        document_type = {"id": str(document.document_type_id), "name": document_type_name}

    plain_text = document.extracted_text
    plain_text_omitted = False
    if plain_text is not None and len(plain_text.encode("utf-8")) > PLAIN_TEXT_MAX_BYTES:
        plain_text = None
        plain_text_omitted = True

    document_body: dict[str, Any] = {
        "id": str(document.uuid),
        "status": document.status.value,
        "file_name": document.file_name,
        "page_range": document.page_range,
        "document_type": document_type,
        "extraction": RawJson(extraction_payload) if extraction_payload is not None else None,
        "plain_text": plain_text,
        "validation": document.validation or [],
        "error": RawJson(document.error) if document.error else None,
        "created_at": optional_datetime_string(document.created_at),
        "updated_at": optional_datetime_string(document.updated_at),
    }
    if plain_text_omitted:
        document_body["plain_text_omitted"] = True

    raw = {
        "event_id": event_id,
        "event": event_type.value,
        "occurred_at": optional_datetime_string(processing_job.finished_at),
        "workflow": {
            "id": str(workflow.uuid),
            "name": workflow.name,
        },
        "processing_job": {
            "id": str(processing_job.uuid),
            "file_name": processing_job.file_name,
            "status": final_status,
            "started_at": optional_datetime_string(processing_job.started_at),
            "finished_at": optional_datetime_string(processing_job.finished_at),
            "duration_ms": processing_job.duration_ms,
        },
        "document": document_body,
    }
    return convert_to_camel_case(raw)
