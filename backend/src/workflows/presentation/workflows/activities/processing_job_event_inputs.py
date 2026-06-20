"""Pydantic inputs for the case-feedback Temporal activities.

Kept in their own module so workflow code can import them inside
`workflow.unsafe.imports_passed_through()` without dragging SQLAlchemy
into the workflow sandbox.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.pipelines import PhaseExecutionEvent
from src.common.domain.enums.processing_job_events import DocumentStatus, JobStatus, JobStep


class ClassifiedDocumentRef(BaseModel):
    document_type_id: UUID | None = None
    document_type_name: str | None = None
    document_index: int
    page_range: dict | None = None


class ReadClassifiedRefsOutput(BaseModel):
    """Compact result of `read_classified_refs` — refs only, never page content.

    The raw classify_pages JSON embeds full per-page text + layout blocks and
    can exceed Temporal's 2 MiB payload limit on large files (TMPRL1103), so
    the heavy parsing happens inside the activity.
    """

    documents: list[ClassifiedDocumentRef]
    total_raw: int = 0


class SplitDocumentRef(BaseModel):
    """One per-document slice of a classify_pages output (E4).

    ``source_uri`` points to an S3 JSON with exactly one classified document
    (``{"documents": [doc]}``) so the extract_fields Lambda can be invoked
    per document without inflating workflow payloads past 2 MiB.
    """

    document_index: int
    source_uri: str


class SplitClassifiedDocumentsOutput(BaseModel):
    documents: list[SplitDocumentRef]


class PersistClassifiedDocumentsInput(BaseModel):
    processing_job_uuid: UUID
    tenant_id: UUID
    workflow_id: UUID
    case_id: UUID | None = None
    file_id: UUID
    documents: list[ClassifiedDocumentRef]
    # Sellado D6': `{document_type_uuid: schema_version}` derivado de los
    # doctype dicts sellados en `DocumentProcessingInput.document_types`
    # (helper `doctype_versions_from_temporal_dicts`). La activity lo estampa
    # en `workflow_documents.document_type_version`. Vacío ⇒ versión NULL
    # (runs despachados antes del versionado).
    document_type_versions: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class PersistedDocumentRef(BaseModel):
    document_id: UUID
    document_type_id: UUID | None = None
    document_type_name: str | None = None
    document_index: int
    page_range: dict | None = None


class PersistClassifiedDocumentsOutput(BaseModel):
    documents: list[PersistedDocumentRef]


class PersistDocumentTextsInput(BaseModel):
    """Input for `persist_document_texts` — slice + persist plain text in-activity.

    `source` is the extract_text S3 output; the OCR JSON (and even the sliced
    text of a big document) can exceed Temporal's payload limit, so neither may
    travel through workflow history.
    """

    source: str
    documents: list[PersistedDocumentRef]

    model_config = ConfigDict(extra="forbid")


class UpdateWorkflowProcessingJobStatusInput(BaseModel):
    processing_job_uuid: UUID
    status: JobStatus
    current_step: JobStep | None = None
    last_seq: int
    error: dict | None = None
    extracted_text_key: str | None = None
    classified_pages_key: str | None = None

    model_config = ConfigDict(extra="forbid")


class RecordPhaseExecutionInput(BaseModel):
    """Input for ``record_phase_execution`` — one recipe-phase boundary.

    ``output_snapshot`` carries a compact, bounded JSON of the artifact the phase
    produced (S3 refs + metadata only; capped in the interpreter so it never
    inflates Temporal history past 2 MiB).
    """

    processing_job_uuid: UUID
    tenant_id: UUID
    seq: int
    phase_id: str
    phase_kind: str
    event: PhaseExecutionEvent
    started_at: datetime | None = None
    finished_at: datetime | None = None
    output_snapshot: dict | None = None
    error: dict | None = None

    model_config = ConfigDict(extra="forbid")


class MarkDocumentInput(BaseModel):
    document_id: UUID
    status: DocumentStatus
    extraction: dict | None = None
    mapped_extraction: dict | None = None
    field_confidence: dict | None = None  # F4 · per-field confidence
    needs_clarification: list | None = None  # F4 · confidence_gate labels
    validation: list | None = None
    extracted_text: str | None = None
    error: dict | None = None

    model_config = ConfigDict(extra="forbid")


class AssessDocumentInput(BaseModel):
    """Input for `assess_document` — capa-2 de confianza por documento (E3).

    `extract_text_source` es la URI S3 del artefacto extract_text: en el punto
    de la receta donde corre assess (entre extract_fields y validate),
    `workflow_documents.extracted_text` AÚN no está en BD, así que la activity
    descarga el JSON y slicea por `page_range` ella misma (mismo patrón que
    `persist_document_texts`). `fields` viaja compacto (`{campo: valor}`, sin
    bboxes) para respetar el límite de 2 MiB de Temporal.
    """

    document_id: UUID
    tenant_id: UUID | None = None
    extract_text_source: str
    page_range: dict | None = None
    document_type_name: str | None = None
    fields: dict
    # phases-config · assess.provider override ("provider:model"); None ⇒ env.
    provider: str | None = None
    # phases-config · assess.min_confidence: campos con extract_confidence por
    # debajo se marcan needs_clarification. None ⇒ flag solo por signals (hoy).
    min_confidence: float | None = None

    model_config = ConfigDict(extra="forbid")


class AssessDocumentOutput(BaseModel):
    """Resumen compacto para el checkpoint STEP_COMPLETED de la fase."""

    assessed: bool = False
    fields_assessed: int = 0
    flagged: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class DispatchProcessingJobWebhookInput(BaseModel):
    """Input for the dispatch_processing_job_webhook activity (spec §4.6)."""

    processing_job_uuid: UUID
    workflow_id: UUID
    run_id: str  # Temporal workflow.info().run_id → WorkflowEvent.idempotency_key
    final_status: str  # JobStatus.value: COMPLETED | PARTIAL | FAILED
    # phases-config · finalize.webhook_projection: subconjunto de campos en el
    # `extraction` del webhook document.extracted. None ⇒ todos (hoy).
    webhook_projection: list[str] | None = None

    model_config = ConfigDict(extra="forbid")
