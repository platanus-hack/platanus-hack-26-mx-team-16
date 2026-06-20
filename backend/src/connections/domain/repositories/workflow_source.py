from abc import ABC, abstractmethod
from uuid import UUID

from src.connections.domain.models.workflow_source import WorkflowSource


class WorkflowSourceRepository(ABC):
    """Persistence for configurable ingest Sources (F8)."""

    @abstractmethod
    async def find_by_route_token(self, route_token: str) -> WorkflowSource | None:
        """Resolve the routing identity from ``POST /v1/ingest/{token}`` (D7)."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, source_id: UUID, tenant_id: UUID) -> WorkflowSource | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_workflow(self, workflow_id: UUID, tenant_id: UUID) -> list[WorkflowSource]:
        raise NotImplementedError

    @abstractmethod
    async def create(self, source: WorkflowSource) -> WorkflowSource:
        raise NotImplementedError

    @abstractmethod
    async def update(self, source: WorkflowSource) -> WorkflowSource:
        """Persist the full entity (mutable: ``enabled``, ``auth_mode``, ``secret``)."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, source_id: UUID, tenant_id: UUID) -> None:
        raise NotImplementedError
