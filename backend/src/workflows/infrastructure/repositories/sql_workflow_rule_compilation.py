"""SQLAlchemy implementation of WorkflowRuleCompilationRepository."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilationORM,
)
from src.common.domain.enums.workflow_rules import WorkflowRuleCompilationStatus
from src.common.domain.exceptions.workflow_rules import (
    WorkflowRuleCompilationNotFoundError,
)
from src.common.domain.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilation,
)
from src.common.infrastructure.helpers.database import atomic_transaction
from src.workflows.domain.rules.repositories.workflow_rule_compilation import (
    WorkflowRuleCompilationRepository,
)
from src.workflows.infrastructure.builders.workflow_rule_compilation import (
    build_workflow_rule_compilation,
)


class SQLWorkflowRuleCompilationRepository(WorkflowRuleCompilationRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, compilation_id: UUID) -> WorkflowRuleCompilation | None:
        stmt = select(WorkflowRuleCompilationORM).where(
            WorkflowRuleCompilationORM.uuid == compilation_id,
        )
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return build_workflow_rule_compilation(orm) if orm else None

    async def list_by_rule(self, rule_id: UUID) -> list[WorkflowRuleCompilation]:
        stmt = (
            select(WorkflowRuleCompilationORM)
            .where(WorkflowRuleCompilationORM.rule_id == rule_id)
            .order_by(desc(WorkflowRuleCompilationORM.version))
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [build_workflow_rule_compilation(orm) for orm in rows]

    async def find_latest_for_rule(self, rule_id: UUID) -> WorkflowRuleCompilation | None:
        stmt = (
            select(WorkflowRuleCompilationORM)
            .where(WorkflowRuleCompilationORM.rule_id == rule_id)
            .order_by(desc(WorkflowRuleCompilationORM.version))
            .limit(1)
        )
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return build_workflow_rule_compilation(orm) if orm else None

    async def create(self, compilation: WorkflowRuleCompilation) -> WorkflowRuleCompilation:
        async with atomic_transaction(self.session):
            next_version_stmt = select(func.coalesce(func.max(WorkflowRuleCompilationORM.version) + 1, 1)).where(
                WorkflowRuleCompilationORM.rule_id == compilation.rule_id
            )
            next_version = (await self.session.execute(next_version_stmt)).scalar_one()

            orm = WorkflowRuleCompilationORM(
                uuid=compilation.uuid,
                rule_id=compilation.rule_id,
                version=next_version,
                kind=compilation.kind,
                status=compilation.status.value,
                artifact=compilation.artifact,
                compiled_with=compilation.compiled_with,
                error=compilation.error,
                completed_at=compilation.completed_at,
            )
            self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_workflow_rule_compilation(orm)

    async def update(self, compilation: WorkflowRuleCompilation) -> WorkflowRuleCompilation:
        async with atomic_transaction(self.session):
            stmt = select(WorkflowRuleCompilationORM).where(WorkflowRuleCompilationORM.uuid == compilation.uuid)
            try:
                orm = (await self.session.execute(stmt)).scalar_one()
            except NoResultFound as exc:
                raise WorkflowRuleCompilationNotFoundError(str(compilation.uuid)) from exc
            orm.status = compilation.status.value
            orm.artifact = compilation.artifact
            orm.compiled_with = compilation.compiled_with
            orm.error = compilation.error
            orm.completed_at = compilation.completed_at
            await self.session.flush()
            await self.session.refresh(orm)
        return build_workflow_rule_compilation(orm)

    async def mark_status(
        self,
        instance_id: UUID,
        status: WorkflowRuleCompilationStatus,
        *,
        artifact: dict | None = None,
        compiled_with: dict | None = None,
        error: str | None = None,
    ) -> WorkflowRuleCompilation:
        async with atomic_transaction(self.session):
            stmt = select(WorkflowRuleCompilationORM).where(WorkflowRuleCompilationORM.uuid == instance_id)
            try:
                orm = (await self.session.execute(stmt)).scalar_one()
            except NoResultFound as exc:
                raise WorkflowRuleCompilationNotFoundError(str(instance_id)) from exc
            orm.status = status.value
            if artifact is not None:
                orm.artifact = artifact
            if compiled_with is not None:
                orm.compiled_with = compiled_with
            if error is not None:
                orm.error = error
            if status.is_terminal:
                orm.completed_at = datetime.now(UTC)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_workflow_rule_compilation(orm)
