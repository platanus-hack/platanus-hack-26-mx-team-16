from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.enums.workflow_rules import WorkflowRuleCompilationStatus
from src.common.domain.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilation,
)


class WorkflowRuleCompilationRepository(ABC):
    @abstractmethod
    async def find_by_id(self, compilation_id: UUID) -> WorkflowRuleCompilation | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_rule(self, rule_id: UUID) -> list[WorkflowRuleCompilation]:
        raise NotImplementedError

    @abstractmethod
    async def find_latest_for_rule(self, rule_id: UUID) -> WorkflowRuleCompilation | None:
        raise NotImplementedError

    @abstractmethod
    async def create(self, compilation: WorkflowRuleCompilation) -> WorkflowRuleCompilation:
        raise NotImplementedError

    @abstractmethod
    async def update(self, compilation: WorkflowRuleCompilation) -> WorkflowRuleCompilation:
        raise NotImplementedError

    @abstractmethod
    async def mark_status(
        self,
        instance_id: UUID,
        status: WorkflowRuleCompilationStatus,
        *,
        artifact: dict | None = None,
        compiled_with: dict | None = None,
        error: str | None = None,
    ) -> WorkflowRuleCompilation:
        raise NotImplementedError
