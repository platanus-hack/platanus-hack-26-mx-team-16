from abc import ABC, abstractmethod
from uuid import UUID

from src.workflows.domain.models.tool import ToolDefinition


class ToolRepository(ABC):
    """Persistence for the workflow-scoped Tool registry (F5 · A3)."""

    @abstractmethod
    async def find_by_id(self, tool_id: UUID, tenant_id: UUID) -> ToolDefinition | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_name(
        self, name: str, workflow_id: UUID, tenant_id: UUID
    ) -> ToolDefinition | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_workflow(self, workflow_id: UUID, tenant_id: UUID) -> list[ToolDefinition]:
        raise NotImplementedError

    @abstractmethod
    async def upsert(self, tool: ToolDefinition) -> ToolDefinition:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, tool_id: UUID, workflow_id: UUID, tenant_id: UUID) -> None:
        raise NotImplementedError
