from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.models.processing.workflow import Workflow


class WorkflowRepository(ABC):
    @abstractmethod
    async def find_by_id(self, workflow_id: UUID, tenant_id: UUID) -> Workflow | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID, industry_id: UUID | None = None) -> list[Workflow]:
        raise NotImplementedError

    @abstractmethod
    async def create(self, workflow: Workflow) -> Workflow:
        raise NotImplementedError

    @abstractmethod
    async def update(self, workflow: Workflow) -> Workflow:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, workflow_id: UUID, tenant_id: UUID) -> None:
        raise NotImplementedError
