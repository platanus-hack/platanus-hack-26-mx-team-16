from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository


@dataclass
class WorkflowRuleLister(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    rule_repository: WorkflowRuleRepository

    async def execute(self) -> list[WorkflowRule]:
        return await self.rule_repository.list_by_workflow(self.workflow_id, self.tenant_id)
