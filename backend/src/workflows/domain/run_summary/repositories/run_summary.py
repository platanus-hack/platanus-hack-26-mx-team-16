from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.enums.run_summary import NarrativeStatus
from src.common.domain.models.processing.workflow_analysis_run_summary import (
    WorkflowAnalysisRunSummary,
)


class WorkflowAnalysisRunSummaryRepository(ABC):
    @abstractmethod
    async def find_by_run(self, run_id: UUID, tenant_id: UUID) -> WorkflowAnalysisRunSummary | None:
        raise NotImplementedError

    @abstractmethod
    async def upsert(self, summary: WorkflowAnalysisRunSummary) -> WorkflowAnalysisRunSummary:
        """Insert or update by `workflow_analysis_run_id` (unique)."""
        raise NotImplementedError

    @abstractmethod
    async def update_narrative(
        self,
        run_id: UUID,
        tenant_id: UUID,
        *,
        status: NarrativeStatus,
        output: dict | None = None,
        output_provenance: dict | None = None,
        output_schema_snapshot: dict | None = None,
        synthesis_template_snapshot: str | None = None,
        narrative_error: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        input_hash: str | None = None,
    ) -> WorkflowAnalysisRunSummary:
        """Patch only the narrative columns. Verdict layer is left untouched."""
        raise NotImplementedError

    @abstractmethod
    async def delete_by_run(self, run_id: UUID, tenant_id: UUID) -> None:
        raise NotImplementedError
