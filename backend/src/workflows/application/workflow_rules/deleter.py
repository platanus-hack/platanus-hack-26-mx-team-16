from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository


@dataclass
class WorkflowRuleDeleter(UseCase):
    rule_id: UUID
    tenant_id: UUID
    rule_repository: WorkflowRuleRepository

    async def execute(self) -> None:
        await self.rule_repository.delete(self.rule_id, self.tenant_id)
