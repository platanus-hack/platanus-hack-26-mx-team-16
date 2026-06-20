"""Read the persisted summary for a run."""

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_analysis_run_summary import (
    WorkflowAnalysisRunSummary,
)
from src.workflows.domain.run_summary.errors import SummaryNotFoundError
from src.workflows.domain.run_summary.repositories.run_summary import (
    WorkflowAnalysisRunSummaryRepository,
)


@dataclass
class GetRunSummary(UseCase):
    run_id: UUID
    tenant_id: UUID
    summary_repository: WorkflowAnalysisRunSummaryRepository

    async def execute(self) -> WorkflowAnalysisRunSummary:
        summary = await self.summary_repository.find_by_run(self.run_id, self.tenant_id)
        if summary is None:
            raise SummaryNotFoundError(str(self.run_id))
        return summary
