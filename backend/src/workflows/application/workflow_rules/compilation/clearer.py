"""Mark the current compilation STALE — used after invalidating edits."""

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.enums.workflow_rules import WorkflowRuleCompilationStatus
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilation,
)
from src.workflows.domain.rules.repositories.workflow_rule_compilation import (
    WorkflowRuleCompilationRepository,
)


@dataclass
class WorkflowRuleCompilationClearer(UseCase):
    compilation_id: UUID
    compilation_repository: WorkflowRuleCompilationRepository

    async def execute(self) -> WorkflowRuleCompilation:
        return await self.compilation_repository.mark_status(
            instance_id=self.compilation_id,
            status=WorkflowRuleCompilationStatus.STALE,
        )
