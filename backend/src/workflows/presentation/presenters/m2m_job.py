"""Presenters del plano M2M: job de extracción + sus documentos (E1).

`GET /v1/jobs/{id}` y la respuesta sync de `POST /v1/extract` comparten esta
forma. `fields` proviene de `field_confidence` ({campo: {value, confidence,
source}} — la capa-1 *parse confidence* por campo, bbox/OCR); `extraction` es
el JSON crudo extraído. La capa-2 (fase `assess`, E3) se mergea por nombre de
campo: cada field gana `extract_confidence` y, si el assess lo flaggeó,
`signals[]`/`explanation`/`candidates[]` (D1 §4.4; D2: viajan inline, sin
HumanTask). `parse_confidence` se mantiene intacto.
"""

from __future__ import annotations

from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob


def present_document(doc: WorkflowDocument) -> dict:
    fields = {
        name: {
            "value": meta.get("value"),
            "parse_confidence": meta.get("confidence"),
            "source": meta.get("source"),
        }
        for name, meta in (doc.field_confidence or {}).items()
        if isinstance(meta, dict)
    }
    for name, confidence in (doc.extract_confidence or {}).items():
        entry = fields.setdefault(name, {"value": None, "parse_confidence": None, "source": None})
        entry["extract_confidence"] = confidence
    for name, meta in (doc.signals or {}).items():
        if not isinstance(meta, dict):
            continue
        entry = fields.setdefault(name, {"value": None, "parse_confidence": None, "source": None})
        entry["signals"] = meta.get("signals") or []
        if meta.get("explanation"):
            entry["explanation"] = meta["explanation"]
        if meta.get("candidates"):
            entry["candidates"] = meta["candidates"]
    return {
        "document_id": str(doc.uuid),
        "document_type_id": str(doc.document_type_id) if doc.document_type_id else None,
        "status": doc.processing_status or (doc.status.value if doc.status else None),
        "fields": fields,
        "extraction": doc.extraction or {},
    }


def present_job(processing_job: WorkflowProcessingJob, documents: list[WorkflowDocument] | None = None) -> dict:
    # NOTE: the M2M wire keys ("job_id", "document_set_id") are a frozen public
    # contract (rename mini-spec §3: CERO cambio). Only the internal attribute
    # access is renamed; the response key names stay byte-for-byte stable.
    payload = {
        "job_id": processing_job.temporal_workflow_id,
        "status": processing_job.status.value,
        "document_set_id": str(processing_job.uuid),
        "workflow_id": str(processing_job.workflow_id),
        "finished_at": processing_job.finished_at.isoformat() if processing_job.finished_at else None,
    }
    if documents is not None:
        payload["documents"] = [present_document(d) for d in documents]
    return payload
