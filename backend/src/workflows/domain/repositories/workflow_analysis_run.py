from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.enums.workflow_rules import WorkflowAnalysisRunStatus
from src.common.domain.models.processing.workflow_analysis_run import WorkflowAnalysisRun


class WorkflowAnalysisRunRepository(ABC):
    @abstractmethod
    async def find_by_id(self, run_id: UUID, tenant_id: UUID) -> WorkflowAnalysisRun | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_case(self, case_id: UUID, tenant_id: UUID) -> list[WorkflowAnalysisRun]:
        raise NotImplementedError

    @abstractmethod
    async def find_active_for_case(self, case_id: UUID, tenant_id: UUID) -> WorkflowAnalysisRun | None:
        raise NotImplementedError

    @abstractmethod
    async def create(self, run: WorkflowAnalysisRun) -> WorkflowAnalysisRun:
        raise NotImplementedError

    @abstractmethod
    async def update_status(
        self,
        run_id: UUID,
        tenant_id: UUID,
        status: WorkflowAnalysisRunStatus,
        error: str | None = None,
        completed: bool = False,
        canceled_by: UUID | None = None,
        rules_passed: int | None = None,
        rules_failed: int | None = None,
        rules_inconclusive: int | None = None,
    ) -> WorkflowAnalysisRun:
        raise NotImplementedError

    @abstractmethod
    async def get_status(self, run_id: UUID, tenant_id: UUID) -> WorkflowAnalysisRunStatus | None:
        raise NotImplementedError
