"""Read-side use cases for WorkflowAnalysisRun."""

import asyncio
from dataclasses import dataclass
from uuid import UUID

from src.common.domain.exceptions.workflow_rules import WorkflowAnalysisRunNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_analysis_run import WorkflowAnalysisRun
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.workflows.domain.repositories.workflow_analysis_run import (
    WorkflowAnalysisRunRepository,
)
from src.workflows.domain.rules.repositories.workflow_rule_result import (
    WorkflowRuleResultRepository,
)


@dataclass
class GetWorkflowAnalysisRunDetail(UseCase):
    run_id: UUID
    tenant_id: UUID
    run_repository: WorkflowAnalysisRunRepository
    result_repository: WorkflowRuleResultRepository

    async def execute(self) -> tuple[WorkflowAnalysisRun, list[WorkflowRuleResult]]:
        run, results = await asyncio.gather(
            self.run_repository.find_by_id(self.run_id, self.tenant_id),
            self.result_repository.list_by_run(self.run_id, self.tenant_id),
        )
        if run is None:
            raise WorkflowAnalysisRunNotFoundError(str(self.run_id))
        return run, results


@dataclass
class ListWorkflowAnalysisRunsForCase(UseCase):
    case_id: UUID
    tenant_id: UUID
    run_repository: WorkflowAnalysisRunRepository

    async def execute(self) -> list[WorkflowAnalysisRun]:
        return await self.run_repository.list_by_case(self.case_id, self.tenant_id)
