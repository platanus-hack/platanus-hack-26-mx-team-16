"""SQLAlchemy implementation of WorkflowSourceRepository (F8)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.workflow_source import WorkflowSourceORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.connections.domain.exceptions import SourceNotFoundError
from src.connections.domain.models.workflow_source import WorkflowSource
from src.connections.domain.repositories.workflow_source import WorkflowSourceRepository
from src.connections.infrastructure.builders.workflow_source import build_workflow_source


class SQLWorkflowSourceRepository(WorkflowSourceRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_route_token(self, route_token: str) -> WorkflowSource | None:
        orm = (
            await self.session.execute(select(WorkflowSourceORM).where(WorkflowSourceORM.route_token == route_token))
        ).scalar_one_or_none()
        return build_workflow_source(orm) if orm else None

    async def find_by_id(self, source_id: UUID, tenant_id: UUID) -> WorkflowSource | None:
        orm = (
            await self.session.execute(
                select(WorkflowSourceORM).where(
                    WorkflowSourceORM.uuid == source_id,
                    WorkflowSourceORM.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()
        return build_workflow_source(orm) if orm else None

    async def list_by_workflow(self, workflow_id: UUID, tenant_id: UUID) -> list[WorkflowSource]:
        stmt = (
            select(WorkflowSourceORM)
            .where(
                WorkflowSourceORM.workflow_id == workflow_id,
                WorkflowSourceORM.tenant_id == tenant_id,
            )
            .order_by(WorkflowSourceORM.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [build_workflow_source(orm) for orm in result.scalars()]

    async def create(self, source: WorkflowSource) -> WorkflowSource:
        async with atomic_transaction(self.session):
            orm = WorkflowSourceORM(
                uuid=source.uuid,
                tenant_id=source.tenant_id,
                workflow_id=source.workflow_id,
                provider=source.provider.value,
                account_id=source.account_id,
                route_token=source.route_token,
                auth_mode=source.auth_mode.value,
                secret=source.secret,
                config=source.config,
                enabled=source.enabled,
            )
            self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_workflow_source(orm)

    async def update(self, source: WorkflowSource) -> WorkflowSource:
        async with atomic_transaction(self.session):
            orm = (
                await self.session.execute(
                    select(WorkflowSourceORM).where(
                        WorkflowSourceORM.uuid == source.uuid,
                        WorkflowSourceORM.tenant_id == source.tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if orm is None:
                raise SourceNotFoundError(str(source.uuid))
            orm.auth_mode = source.auth_mode.value
            orm.secret = source.secret
            orm.config = source.config
            orm.enabled = source.enabled
            await self.session.flush()
            await self.session.refresh(orm)
        return build_workflow_source(orm)

    async def delete(self, source_id: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            orm = (
                await self.session.execute(
                    select(WorkflowSourceORM).where(
                        WorkflowSourceORM.uuid == source_id,
                        WorkflowSourceORM.tenant_id == tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if orm is not None:
                await self.session.delete(orm)
