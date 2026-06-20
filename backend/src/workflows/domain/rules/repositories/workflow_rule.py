from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.models.processing.workflow_rule import WorkflowRule


class WorkflowRuleRepository(ABC):
    @abstractmethod
    async def find_by_id(self, rule_id: UUID, tenant_id: UUID) -> WorkflowRule | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_workflow(self, workflow_id: UUID, tenant_id: UUID) -> list[WorkflowRule]:
        raise NotImplementedError

    @abstractmethod
    async def create(self, rule: WorkflowRule) -> WorkflowRule:
        raise NotImplementedError

    @abstractmethod
    async def update(self, rule: WorkflowRule) -> WorkflowRule:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, rule_id: UUID, tenant_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def reorder(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        ordered_rule_ids: list[UUID],
    ) -> list[WorkflowRule]:
        raise NotImplementedError

    @abstractmethod
    async def set_current_compilation(
        self,
        rule_id: UUID,
        tenant_id: UUID,
        compilation_id: UUID | None,
    ) -> WorkflowRule:
        raise NotImplementedError
