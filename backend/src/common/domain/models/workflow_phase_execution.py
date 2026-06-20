from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.pipelines import PhaseExecutionStatus


class WorkflowPhaseExecution(BaseModel):
    """A single recipe phase that ran inside an interpreter execution."""

    uuid: UUID
    tenant_id: UUID
    processing_job_id: UUID
    seq: int
    phase_id: str
    phase_kind: str
    status: PhaseExecutionStatus = Field(default=PhaseExecutionStatus.RUNNING)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    output_snapshot: dict | None = None
    error: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    @property
    def duration_ms(self) -> int | None:
        """Wall-clock duration of the phase, in ms. ``None`` while still running."""
        if self.started_at is None or self.finished_at is None:
            return None
        delta = self.finished_at - self.started_at
        return int(delta.total_seconds() * 1000)
