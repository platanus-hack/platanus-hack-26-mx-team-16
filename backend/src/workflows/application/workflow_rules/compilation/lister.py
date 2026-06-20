"""List compilations for a given workflow rule."""

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.exceptions.workflow_rules import WorkflowRuleNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilation,
)
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.domain.rules.repositories.workflow_rule_compilation import (
    WorkflowRuleCompilationRepository,
)


@dataclass
class WorkflowRuleCompilationLister(UseCase):
    rule_id: UUID
    tenant_id: UUID
    rule_repository: WorkflowRuleRepository
    compilation_repository: WorkflowRuleCompilationRepository

    async def execute(self) -> list[WorkflowRuleCompilation]:
        rule = await self.rule_repository.find_by_id(self.rule_id, self.tenant_id)
        if rule is None:
            raise WorkflowRuleNotFoundError(str(self.rule_id))
        return await self.compilation_repository.list_by_rule(self.rule_id)
