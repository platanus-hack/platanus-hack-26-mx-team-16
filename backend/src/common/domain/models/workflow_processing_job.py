from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.workflows import (
    WorkflowProcessingJobStatus,
    WorkflowProcessingJobTrigger,
)


class WorkflowProcessingJob(BaseModel):
    uuid: UUID
    temporal_workflow_id: str
    tenant_id: UUID
    workflow_id: UUID
    workflow_case_id: UUID | None = None
    file_id: UUID
    status: WorkflowProcessingJobStatus = Field(default=WorkflowProcessingJobStatus.PENDING)
    attempts: int = 0
    error: str | None = None
    result_summary: dict | None = None
    current_step: str | None = None
    last_seq: int = 0
    extracted_text: str | None = None
    classified_pages: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_by_id: UUID | None = None
    trigger: WorkflowProcessingJobTrigger = Field(default=WorkflowProcessingJobTrigger.USER)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    file_name: str | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    @property
    def duration_ms(self) -> int | None:
        """Wall-clock duration of the run, in ms.

        Computed from ``started_at`` (set when the set is claimed) and
        ``finished_at`` (set on transition to a terminal status). ``None``
        while the run is still pending or in flight.
        """
        if self.started_at is None or self.finished_at is None:
            return None
        delta = self.finished_at - self.started_at
        return int(delta.total_seconds() * 1000)
