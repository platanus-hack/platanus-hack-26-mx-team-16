from dataclasses import dataclass
from uuid import UUID

from src.common.domain.exceptions.workflow_rules import WorkflowRuleNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository


@dataclass
class WorkflowRuleGetter(UseCase):
    rule_id: UUID
    tenant_id: UUID
    rule_repository: WorkflowRuleRepository

    async def execute(self) -> WorkflowRule:
        rule = await self.rule_repository.find_by_id(self.rule_id, self.tenant_id)
        if rule is None:
            raise WorkflowRuleNotFoundError(str(self.rule_id))
        return rule
