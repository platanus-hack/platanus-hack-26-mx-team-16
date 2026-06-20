"""Domain entities for the Dashboard Processing tab.

The Processing tab is live: counters of in-flight documents, distribution
of documents across pipeline stages, and the currently active documents
with their progress.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PipelineStageKey(StrEnum):
    """Dashboard pipeline stage names exposed to the frontend.

    These are dashboard-presentation values, NOT the persistence-level
    enum `WorkflowDocumentStatus`. See `PipelineStage` for the mapping
    rules implemented by the repository.

    PROCESSING is a v1 fallback used when `workflow_documents.processing_status`
    is not yet populated by the Temporal workers — in that case the OCR /
    EXTRACTION / VALIDATION sub-stages collapse into a single PROCESSING
    bucket.
    """

    UPLOAD = "UPLOAD"
    OCR = "OCR"
    EXTRACTION = "EXTRACTION"
    VALIDATION = "VALIDATION"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"


class ProcessingSummary(BaseModel):
    """Counters for the five stat cards above the pipeline view.

    `avg_processing_seconds` is None when no documents have completed
    today (SQL `AVG` over an empty set returns NULL); the frontend
    renders this as "—".
    """

    model_config = ConfigDict(from_attributes=True)

    in_queue: int
    processing: int
    completed_today: int
    failed: int
    avg_processing_seconds: float | None


class PipelineStage(BaseModel):
    """One bar of the pipeline distribution chart.

    `label` is a human-friendly string derived from `stage`. The repository
    is the single source of truth for both the enum value and the label.
    """

    model_config = ConfigDict(from_attributes=True)

    stage: PipelineStageKey
    label: str
    count: int


class LiveProcessingDocument(BaseModel):
    """A document currently being processed, shown in the live list.

    `progress_pct` is a heuristic per `stage` (no real progress is
    persisted today). `eta_seconds` is `avg_processing_seconds_global -
    elapsed_seconds`; None when the document has already exceeded the
    average (the frontend renders this as "—").
    """

    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    name: str
    stage: PipelineStageKey
    progress_pct: int
    eta_seconds: int | None
    started_at: datetime


class ProcessingData(BaseModel):
    """Composite payload returned by `GET /v1/dashboard/processing`."""

    model_config = ConfigDict(from_attributes=True)

    summary: ProcessingSummary
    stages: list[PipelineStage]
    live_processing: list[LiveProcessingDocument]
