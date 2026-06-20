"""Synthesize the SSE replay window for a workflow's processing-jobs.

The Temporal worker publishes events to Redis as the pipeline advances;
the SSE endpoint replays those events from PG when a late subscriber
opens the stream with ``since_seq``. This use case is the deterministic,
testable core of that replay — it pulls the rows the cursor needs and
emits one event per persisted document plus one terminal event per set.

Per-set seq invariant
---------------------
Every event belongs to a `(processing_job_id, seq)` namespace. The browser
reducer drops events with `seq <= lastSeqBySet[setId]`. Two implications:

* Per-document events MUST land with seqs strictly less than the set's
  ``last_seq`` (the terminal seq). Otherwise the terminal event lands
  first, advances the cursor, and the per-doc events are silently
  dropped.
* The replay function therefore back-numbers per-doc events as
  ``last_seq - N + i`` so they appear chronologically before the
  terminal event when the events are sorted by `(processing_job_id, seq)`.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.common.domain.enums.processing_job_events import ProcessingJobEventType
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.workflows.domain.events import ProcessingJobEvent
from src.workflows.domain.utils import count_fields as _count_extraction_fields
from src.workflows.domain.repositories.workflow_document import (
    WorkflowDocumentRepository,
)
from src.workflows.domain.repositories.workflow_processing_job_repository import (
    WorkflowProcessingJobRepository,
)


@dataclass
class ProcessingJobEventReplayer(UseCase):
    """Build the chronological replay window for a workflow's document sets.

    Output ordering: events are sorted by ``(processing_job_id, seq)`` so a
    consumer applying them in order sees per-document events before the
    set's terminal event.
    """

    workflow_id: UUID
    tenant_id: UUID
    since_seq: int
    processing_job_repository: WorkflowProcessingJobRepository
    document_repository: WorkflowDocumentRepository
    workflow_case_id: UUID | None = None
    # Optional lookup so terminal events can carry the source filename for
    # the UI (the live `dispatched` event is not part of the replay window).
    file_names_by_set_id: dict[UUID, str | None] | None = None

    async def execute(self) -> list[ProcessingJobEvent]:
        sets = await self.processing_job_repository.list_for_replay(
            workflow_id=self.workflow_id,
            tenant_id=self.tenant_id,
            since_seq=self.since_seq,
            workflow_case_id=self.workflow_case_id,
        )
        if not sets:
            return []

        docs = await self.document_repository.list_by_processing_job_ids([s.uuid for s in sets], self.tenant_id)
        docs_by_set: dict[UUID, list[WorkflowDocument]] = {}
        for d in docs:
            if d.processing_job_id is None:
                continue
            docs_by_set.setdefault(d.processing_job_id, []).append(d)

        names = self.file_names_by_set_id or {}
        events: list[ProcessingJobEvent] = []
        for s in sets:
            events.extend(_per_doc_events(s, docs_by_set.get(s.uuid, [])))
            terminal = _terminal_event(s, docs_by_set.get(s.uuid, []), file_name=names.get(s.uuid))
            if terminal is not None:
                events.append(terminal)

        events.sort(key=lambda e: (str(e.processing_job_id), e.seq))
        return events


def _per_doc_events(
    processing_job: WorkflowProcessingJob,
    documents: list[WorkflowDocument],
) -> list[ProcessingJobEvent]:
    persisted = [d for d in documents if _processing_status(d) is not None]
    if not persisted:
        return []
    ts = processing_job.updated_at or processing_job.created_at or datetime.now(UTC)
    terminal_seq = processing_job.last_seq
    events: list[ProcessingJobEvent] = []
    for i, doc in enumerate(persisted, start=1):
        seq = max(1, terminal_seq - len(persisted) + i - 1)
        if seq >= terminal_seq:
            seq = i
        events.append(
            ProcessingJobEvent.build(
                type=ProcessingJobEventType.DOCUMENT_PERSISTED,
                seq=seq,
                ts=ts,
                workflow_id=processing_job.workflow_id,
                processing_job_id=processing_job.uuid,
                workflow_case_id=processing_job.workflow_case_id,
                document_id=doc.uuid,
                payload=_doc_payload(doc),
            )
        )
    return events


def _terminal_event(
    processing_job: WorkflowProcessingJob,
    documents: list[WorkflowDocument],
    file_name: str | None = None,
) -> ProcessingJobEvent | None:
    status = processing_job.status
    ts = processing_job.updated_at or processing_job.created_at or datetime.now(UTC)
    started_at = processing_job.started_at.isoformat() if processing_job.started_at else None
    finished_at = processing_job.finished_at.isoformat() if processing_job.finished_at else None
    duration_ms = processing_job.duration_ms
    if status.is_terminal_success:
        return ProcessingJobEvent.build(
            type=ProcessingJobEventType.COMPLETED,
            seq=processing_job.last_seq,
            ts=ts,
            workflow_id=processing_job.workflow_id,
            processing_job_id=processing_job.uuid,
            workflow_case_id=processing_job.workflow_case_id,
            payload={
                "status": status.value,
                "file_name": file_name,
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_ms": duration_ms,
                "document_ids": [str(d.uuid) for d in documents if (s := _processing_status(d)) and s.is_completed],
                "failed_document_ids": [
                    str(d.uuid) for d in documents if (s := _processing_status(d)) and s.is_failed
                ],
            },
        )
    if status.is_failed:
        return ProcessingJobEvent.build(
            type=ProcessingJobEventType.FAILED,
            seq=processing_job.last_seq,
            ts=ts,
            workflow_id=processing_job.workflow_id,
            processing_job_id=processing_job.uuid,
            workflow_case_id=processing_job.workflow_case_id,
            payload={
                "error_code": "workflow.error",
                "message": processing_job.error or "",
                "source_step": processing_job.current_step,
                "file_name": file_name,
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_ms": duration_ms,
            },
        )
    return None


def _processing_status(doc: WorkflowDocument):
    """Return the doc's processing_status as DocumentStatus enum if terminal."""
    from src.common.domain.enums.processing_job_events import DocumentStatus

    raw = doc.processing_status
    if raw is None:
        return None
    try:
        status = DocumentStatus(raw)
    except ValueError:
        return None
    return status if status.is_terminal else None


def _doc_payload(doc: WorkflowDocument) -> dict[str, Any]:
    return {
        "processing_status": doc.processing_status,
        "document_type_id": (str(doc.document_type_id) if doc.document_type_id else None),
        "document_type_name": doc.file_name,
        "document_index": doc.document_index,
        "page_range": doc.page_range,
        "summary": {
            "extracted_field_count": _count_extraction_fields(doc.extraction),
            "validation_pass_count": _count_validation_status(doc.validation, status="passed"),
            "validation_fail_count": _count_validation_status(doc.validation, status="failed"),
        },
    }


def _count_validation_status(items: object, *, status: str) -> int:
    if not isinstance(items, list):
        return 0
    return sum(1 for v in items if isinstance(v, dict) and v.get("status") == status)
