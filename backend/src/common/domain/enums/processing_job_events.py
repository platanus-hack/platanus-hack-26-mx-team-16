"""Enums for the processing-job live-feedback event bus.

Event types travel from the Temporal workflow via Redis Pub/Sub to the
browser SSE consumer; the same names are mirrored in the frontend at
`frontend/src/domain/events/processing-job-events.ts`.

`JobStatus`, `JobStep` and `DocumentStatus` describe lifecycle states
consumed by activity inputs (e.g. ``UpdateWorkflowProcessingJobStatusInput``)
and live here alongside the event-type enum to keep the case-detail
feedback bus enums grouped.
"""

from enum import StrEnum


class ProcessingJobEventType(StrEnum):
    DISPATCHED = "processing_job.dispatched"
    STEP_STARTED = "processing_job.step_started"
    STEP_COMPLETED = "processing_job.step_completed"
    COMPLETED = "processing_job.completed"
    FAILED = "processing_job.failed"
    DOCUMENT_PERSISTED = "processing_job.document_persisted"


class JobStep(StrEnum):
    EXTRACT_TEXT = "extract_text"
    CLASSIFY_PAGES = "classify_pages"
    PERSIST_DOCS = "persist_documents"
    EXTRACT_FIELDS = "extract_fields"
    VALIDATE = "validate_extraction"


class JobStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in (DocumentStatus.COMPLETED, DocumentStatus.FAILED)

    @property
    def is_completed(self) -> bool:
        return self is DocumentStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self is DocumentStatus.FAILED
