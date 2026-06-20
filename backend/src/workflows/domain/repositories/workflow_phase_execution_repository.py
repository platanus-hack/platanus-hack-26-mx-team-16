from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.common.domain.enums.pipelines import PhaseExecutionStatus
from src.common.domain.models.workflow_phase_execution import WorkflowPhaseExecution


class WorkflowPhaseExecutionRepository(ABC):
    @abstractmethod
    async def list_by_job(self, processing_job_id: UUID) -> list[WorkflowPhaseExecution]:
        """Per-phase rows of a run, ordered by ``seq`` (recipe order)."""
        raise NotImplementedError

    @abstractmethod
    async def record_started(
        self,
        *,
        processing_job_id: UUID,
        tenant_id: UUID,
        seq: int,
        phase_id: str,
        phase_kind: str,
        started_at: datetime | None,
    ) -> None:
        """Open a phase row (RUNNING). Idempotent on ``(processing_job_id, seq)``."""
        raise NotImplementedError

    @abstractmethod
    async def record_finished(
        self,
        *,
        processing_job_id: UUID,
        tenant_id: UUID,
        seq: int,
        phase_id: str,
        phase_kind: str,
        status: PhaseExecutionStatus,
        started_at: datetime | None,
        finished_at: datetime | None,
        output_snapshot: dict | None,
        error: dict | None,
    ) -> None:
        """Close a phase row (COMPLETED/FAILED). Upserts so a finish without a
        prior start still records the phase."""
        raise NotImplementedError
