"""SQLAlchemy implementation of ToolRepository (F5, workflow-scoped)."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.tool_definition import ToolDefinitionORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.workflows.domain.models.tool import ToolDefinition
from src.workflows.domain.repositories.tool import ToolRepository
from src.workflows.infrastructure.builders.tool import build_tool_definition


class SQLToolRepository(ToolRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, tool_id: UUID, tenant_id: UUID) -> ToolDefinition | None:
        stmt = select(ToolDefinitionORM).where(
            ToolDefinitionORM.uuid == tool_id,
            ToolDefinitionORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        try:
            return build_tool_definition(result.scalar_one())
        except NoResultFound:
            return None

    async def find_by_name(
        self, name: str, workflow_id: UUID, tenant_id: UUID
    ) -> ToolDefinition | None:
        stmt = select(ToolDefinitionORM).where(
            ToolDefinitionORM.name == name,
            ToolDefinitionORM.workflow_id == workflow_id,
            ToolDefinitionORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        try:
            return build_tool_definition(result.scalar_one())
        except NoResultFound:
            return None

    async def list_by_workflow(self, workflow_id: UUID, tenant_id: UUID) -> list[ToolDefinition]:
        stmt = (
            select(ToolDefinitionORM)
            .where(
                ToolDefinitionORM.workflow_id == workflow_id,
                ToolDefinitionORM.tenant_id == tenant_id,
            )
            .order_by(ToolDefinitionORM.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [build_tool_definition(orm) for orm in result.scalars()]

    async def upsert(self, tool: ToolDefinition) -> ToolDefinition:
        async with atomic_transaction(self.session):
            stmt = select(ToolDefinitionORM).where(
                ToolDefinitionORM.workflow_id == tool.workflow_id,
                ToolDefinitionORM.name == tool.name,
            )
            existing = (await self.session.execute(stmt)).scalar_one_or_none()
            if existing is None:
                existing = ToolDefinitionORM(
                    uuid=tool.uuid,
                    tenant_id=tool.tenant_id,
                    workflow_id=tool.workflow_id,
                    name=tool.name,
                )
                self.session.add(existing)
            existing.display_name = tool.display_name
            existing.description = tool.description
            existing.transport = tool.transport.value
            existing.connection_account_id = tool.connection_account_id
            existing.input_schema = tool.input_schema
            existing.output_schema = tool.output_schema
            existing.config = tool.config
            existing.enabled = tool.enabled
            await self.session.flush()
            await self.session.refresh(existing)
        return build_tool_definition(existing)

    async def delete(self, tool_id: UUID, workflow_id: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            stmt = delete(ToolDefinitionORM).where(
                ToolDefinitionORM.uuid == tool_id,
                ToolDefinitionORM.workflow_id == workflow_id,
                ToolDefinitionORM.tenant_id == tenant_id,
            )
            await self.session.execute(stmt)
