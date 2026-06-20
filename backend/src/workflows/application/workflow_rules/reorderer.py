from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository


@dataclass
class WorkflowRulesReorderer(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    ordered_rule_ids: list[UUID]
    rule_repository: WorkflowRuleRepository

    async def execute(self) -> list[WorkflowRule]:
        return await self.rule_repository.reorder(
            workflow_id=self.workflow_id,
            tenant_id=self.tenant_id,
            ordered_rule_ids=self.ordered_rule_ids,
        )
