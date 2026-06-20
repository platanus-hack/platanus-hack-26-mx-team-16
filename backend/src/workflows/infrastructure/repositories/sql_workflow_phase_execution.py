from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.workflow_phase_execution import WorkflowPhaseExecutionORM
from src.common.domain.enums.pipelines import PhaseExecutionStatus
from src.common.domain.models.workflow_phase_execution import WorkflowPhaseExecution
from src.workflows.domain.repositories.workflow_phase_execution_repository import (
    WorkflowPhaseExecutionRepository,
)

_CONFLICT_KEYS = ["processing_job_id", "seq"]


class SQLWorkflowPhaseExecutionRepository(WorkflowPhaseExecutionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_job(self, processing_job_id: UUID) -> list[WorkflowPhaseExecution]:
        stmt = (
            select(WorkflowPhaseExecutionORM)
            .where(WorkflowPhaseExecutionORM.processing_job_id == processing_job_id)
            .order_by(WorkflowPhaseExecutionORM.seq.asc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [WorkflowPhaseExecution.model_validate(row) for row in rows]

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
        # ON CONFLICT DO NOTHING: a retried "started" never clobbers a row that a
        # later "finished" may already have closed (Temporal at-least-once).
        stmt = (
            pg_insert(WorkflowPhaseExecutionORM)
            .values(
                processing_job_id=processing_job_id,
                tenant_id=tenant_id,
                seq=seq,
                phase_id=phase_id,
                phase_kind=phase_kind,
                status=PhaseExecutionStatus.RUNNING.value,
                started_at=started_at,
            )
            .on_conflict_do_nothing(index_elements=_CONFLICT_KEYS)
        )
        await self.session.execute(stmt)
        await self.session.flush()

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
        # Upsert: if the "started" row exists, close it; if it was missed, create
        # the row already closed (keeps the timeline complete either way).
        stmt = pg_insert(WorkflowPhaseExecutionORM).values(
            processing_job_id=processing_job_id,
            tenant_id=tenant_id,
            seq=seq,
            phase_id=phase_id,
            phase_kind=phase_kind,
            status=status.value,
            started_at=started_at,
            finished_at=finished_at,
            output_snapshot=output_snapshot,
            error=error,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=_CONFLICT_KEYS,
            set_={
                "status": status.value,
                "phase_id": phase_id,
                "phase_kind": phase_kind,
                "finished_at": finished_at,
                "output_snapshot": output_snapshot,
                "error": error,
            },
        )
        await self.session.execute(stmt)
        await self.session.flush()
