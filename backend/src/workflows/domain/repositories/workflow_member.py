from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.models.workflow_member import WorkflowMember


class WorkflowMemberRepository(ABC):
    """Persistence for explicit per-workflow member grants (workflow permissions)."""

    @abstractmethod
    async def list_by_workflow(self, workflow_id: UUID, tenant_id: UUID) -> list[WorkflowMember]:
        """All members of the workflow, enriched with profile data, oldest first."""
        raise NotImplementedError

    @abstractmethod
    async def find(self, workflow_id: UUID, user_id: UUID, tenant_id: UUID) -> WorkflowMember | None:
        raise NotImplementedError

    @abstractmethod
    async def list_workflow_ids_for_user(self, user_id: UUID, tenant_id: UUID) -> list[UUID]:
        """Ids of workflows the user is an explicit member of (for list filtering)."""
        raise NotImplementedError

    @abstractmethod
    async def add(self, member: WorkflowMember) -> WorkflowMember:
        raise NotImplementedError

    @abstractmethod
    async def update_role(
        self, workflow_id: UUID, user_id: UUID, tenant_id: UUID, role: str
    ) -> WorkflowMember:
        raise NotImplementedError

    @abstractmethod
    async def remove(self, workflow_id: UUID, user_id: UUID, tenant_id: UUID) -> None:
        raise NotImplementedError
