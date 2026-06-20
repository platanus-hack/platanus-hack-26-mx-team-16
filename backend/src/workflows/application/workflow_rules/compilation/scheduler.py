"""Enqueue a compilation row in PENDING state (spec §10.2)."""

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.enums.workflow_rules import WorkflowRuleCompilationStatus
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
class WorkflowRuleCompilationScheduler(UseCase):
    rule_id: UUID
    tenant_id: UUID
    rule_repository: WorkflowRuleRepository
    compilation_repository: WorkflowRuleCompilationRepository

    async def execute(self) -> WorkflowRuleCompilation:
        rule = await self.rule_repository.find_by_id(self.rule_id, self.tenant_id)
        if not rule:
            raise WorkflowRuleNotFoundError(str(self.rule_id))

        compilation = WorkflowRuleCompilation(
            rule_id=self.rule_id,
            version=0,  # actual value assigned by the repo on insert
            kind=rule.kind,
            status=WorkflowRuleCompilationStatus.PENDING,
        )
        return await self.compilation_repository.create(compilation)
