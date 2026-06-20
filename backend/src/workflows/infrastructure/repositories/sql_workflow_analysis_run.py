"""SQLAlchemy implementation of WorkflowAnalysisRunRepository."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.processing.workflow_analysis_run import WorkflowAnalysisRunORM
from src.common.domain.enums.workflow_rules import WorkflowAnalysisRunStatus
from src.common.domain.exceptions.workflow_rules import WorkflowAnalysisRunNotFoundError
from src.common.domain.models.processing.workflow_analysis_run import WorkflowAnalysisRun
from src.common.infrastructure.helpers.database import atomic_transaction
from src.workflows.domain.repositories.workflow_analysis_run import (
    WorkflowAnalysisRunRepository,
)
from src.workflows.infrastructure.builders.analysis_run import (
    build_workflow_analysis_run,
)


class SQLWorkflowAnalysisRunRepository(WorkflowAnalysisRunRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, run_id: UUID, tenant_id: UUID) -> WorkflowAnalysisRun | None:
        stmt = select(WorkflowAnalysisRunORM).where(
            WorkflowAnalysisRunORM.uuid == run_id,
            WorkflowAnalysisRunORM.tenant_id == tenant_id,
        )
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return build_workflow_analysis_run(orm) if orm else None

    async def list_by_case(self, case_id: UUID, tenant_id: UUID) -> list[WorkflowAnalysisRun]:
        stmt = (
            select(WorkflowAnalysisRunORM)
            .where(
                WorkflowAnalysisRunORM.workflow_case_id == case_id,
                WorkflowAnalysisRunORM.tenant_id == tenant_id,
            )
            .order_by(WorkflowAnalysisRunORM.created_at.desc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [build_workflow_analysis_run(orm) for orm in rows]

    async def find_active_for_case(self, case_id: UUID, tenant_id: UUID) -> WorkflowAnalysisRun | None:
        stmt = select(WorkflowAnalysisRunORM).where(
            WorkflowAnalysisRunORM.workflow_case_id == case_id,
            WorkflowAnalysisRunORM.tenant_id == tenant_id,
            WorkflowAnalysisRunORM.status.in_(
                [
                    WorkflowAnalysisRunStatus.RUNNING,
                    WorkflowAnalysisRunStatus.CANCELING,
                ]
            ),
        )
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return build_workflow_analysis_run(orm) if orm else None

    async def create(self, run: WorkflowAnalysisRun) -> WorkflowAnalysisRun:
        async with atomic_transaction(self.session):
            orm = WorkflowAnalysisRunORM(
                uuid=run.uuid,
                tenant_id=run.tenant_id,
                workflow_id=run.workflow_id,
                workflow_case_id=run.workflow_case_id,
                status=run.status.value,
                trigger=run.trigger.value,
                triggered_by=run.triggered_by,
                started_at=run.started_at or datetime.now(UTC),
                reviewer_model=run.reviewer_model,
                critic_model=run.critic_model,
                consensus_samples=run.consensus_samples,
                rules_total=run.rules_total,
            )
            self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_workflow_analysis_run(orm)

    async def update_status(
        self,
        run_id: UUID,
        tenant_id: UUID,
        status: WorkflowAnalysisRunStatus,
        error: str | None = None,
        completed: bool = False,
        canceled_by: UUID | None = None,
        rules_passed: int | None = None,
        rules_failed: int | None = None,
        rules_inconclusive: int | None = None,
    ) -> WorkflowAnalysisRun:
        async with atomic_transaction(self.session):
            stmt = select(WorkflowAnalysisRunORM).where(
                WorkflowAnalysisRunORM.uuid == run_id,
                WorkflowAnalysisRunORM.tenant_id == tenant_id,
            )
            try:
                orm = (await self.session.execute(stmt)).scalar_one()
            except NoResultFound as exc:
                raise WorkflowAnalysisRunNotFoundError(str(run_id)) from exc

            orm.status = status.value
            if error is not None:
                orm.error = error
            if completed:
                orm.completed_at = datetime.now(UTC)
            if status == WorkflowAnalysisRunStatus.CANCELED:
                orm.canceled_at = datetime.now(UTC)
                orm.canceled_by = canceled_by
            if rules_passed is not None:
                orm.rules_passed = rules_passed
            if rules_failed is not None:
                orm.rules_failed = rules_failed
            if rules_inconclusive is not None:
                orm.rules_inconclusive = rules_inconclusive

            await self.session.flush()
            await self.session.refresh(orm)
        return build_workflow_analysis_run(orm)

    async def get_status(self, run_id: UUID, tenant_id: UUID) -> WorkflowAnalysisRunStatus | None:
        stmt = select(WorkflowAnalysisRunORM.status).where(
            WorkflowAnalysisRunORM.uuid == run_id,
            WorkflowAnalysisRunORM.tenant_id == tenant_id,
        )
        value = (await self.session.execute(stmt)).scalar_one_or_none()
        return WorkflowAnalysisRunStatus(value) if value else None
