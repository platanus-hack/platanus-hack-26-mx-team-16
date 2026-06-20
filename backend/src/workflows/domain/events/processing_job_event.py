"""ProcessingJobEvent — concrete event type carried over the per-workflow channel.

Channel: ``workflow:{workflow_id}:processing_jobs:events``. The frontend opens a
single EventSource per workflow and uses the embedded ``processing_job_id``
(and optional ``workflow_case_id`` / ``document_id``) to demux when multiple
processing-jobs run concurrently.
"""

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict

from src.common.domain.enums.processing_job_events import ProcessingJobEventType
from src.common.domain.events.base import Event


def processing_job_channel(workflow_id: UUID) -> str:
    return f"workflow:{workflow_id}:processing_jobs:events"


class ProcessingJobEvent(Event):
    type: ProcessingJobEventType
    workflow_id: UUID
    processing_job_id: UUID
    workflow_case_id: UUID | None = None
    document_id: UUID | None = None

    model_config = ConfigDict(extra="forbid")

    @property
    def channel(self) -> str:
        return processing_job_channel(self.workflow_id)

    @classmethod
    def build(
        cls,
        *,
        type: ProcessingJobEventType,
        seq: int,
        ts: datetime,
        workflow_id: UUID,
        processing_job_id: UUID,
        payload: dict,
        workflow_case_id: UUID | None = None,
        document_id: UUID | None = None,
    ) -> "ProcessingJobEvent":
        return cls(
            seq=seq,
            ts=ts,
            type=type,
            workflow_id=workflow_id,
            processing_job_id=processing_job_id,
            workflow_case_id=workflow_case_id,
            document_id=document_id,
            payload=payload,
        )
