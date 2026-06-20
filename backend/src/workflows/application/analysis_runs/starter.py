"""Start a new WorkflowAnalysisRun for a case and launch its Temporal workflow."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from temporalio.client import Client as TemporalClient

from src.common.application.logging import get_logger
from src.common.domain.entities.workflows.analysis_run_processing import (
    AnalysisRunWorkflowInput,
)
from src.common.domain.enums.workflow_rules import (
    WorkflowAnalysisRunStatus,
    WorkflowAnalysisRunTrigger,
)
from src.common.domain.exceptions.processing import (
    AnalysisAlreadyRunningError,
    CaseNotFoundError,
    WorkflowNotFoundError,
)
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_analysis_run import WorkflowAnalysisRun
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_analysis_run import (
    WorkflowAnalysisRunRepository,
)
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.presentation.workflows import (
    WorkflowAnalysisRunWorkflow,
    workflow_id_for_run,
)

logger = get_logger(__name__)


@dataclass
class StartWorkflowAnalysisRun(UseCase):
    workflow_id: UUID
    case_id: UUID
    tenant_id: UUID
    triggered_by: UUID | None
    workflow_repository: WorkflowRepository
    case_repository: WorkflowCaseRepository
    run_repository: WorkflowAnalysisRunRepository
    temporal_client: TemporalClient
    task_queue: str

    async def execute(self) -> WorkflowAnalysisRun:
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if not workflow:
            raise WorkflowNotFoundError(str(self.workflow_id))
        case = await self.case_repository.find_by_id(self.case_id, self.tenant_id)
        if not case:
            raise CaseNotFoundError(str(self.case_id))

        active = await self.run_repository.find_active_for_case(self.case_id, self.tenant_id)
        if active:
            raise AnalysisAlreadyRunningError(str(self.case_id))

        run = WorkflowAnalysisRun(
            uuid=uuid4(),
            tenant_id=self.tenant_id,
            workflow_id=self.workflow_id,
            workflow_case_id=self.case_id,
            status=WorkflowAnalysisRunStatus.RUNNING,
            trigger=WorkflowAnalysisRunTrigger.USER,
            triggered_by=self.triggered_by,
            started_at=datetime.now(UTC),
        )
        persisted = await self.run_repository.create(run)

        # Kick off the Temporal orchestrator. If the call fails we revert
        # the row to FAILED so it doesn't sit RUNNING with no executor.
        try:
            await self.temporal_client.start_workflow(
                WorkflowAnalysisRunWorkflow.run,
                AnalysisRunWorkflowInput(
                    run_id=persisted.uuid,
                    workflow_id=self.workflow_id,
                    case_id=self.case_id,
                    tenant_id=self.tenant_id,
                ),
                id=workflow_id_for_run(persisted.uuid),
                task_queue=self.task_queue,
            )
        except Exception as exc:
            logger.exception(
                "analysis_run.start_workflow_failed",
                run_id=str(persisted.uuid),
            )
            await self.run_repository.update_status(
                run_id=persisted.uuid,
                tenant_id=self.tenant_id,
                status=WorkflowAnalysisRunStatus.FAILED,
                error=f"temporal.start: {exc}",
                completed=True,
            )
            raise

        return persisted
