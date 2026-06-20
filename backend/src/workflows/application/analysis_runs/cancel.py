"""Cancel a running WorkflowAnalysisRun.

Sends a `cancel` signal to the running Temporal workflow so the
orchestrator can stop scheduling new evaluations, flush a final
`RUN_CANCELED` event, and flip the DB row. If the workflow handle is
gone (already finished or never started), we fall back to flipping the
row directly so the API never leaves a run hanging in `RUNNING`.
"""

from dataclasses import dataclass
from uuid import UUID

from temporalio.client import Client as TemporalClient
from temporalio.service import RPCError

from src.common.application.logging import get_logger
from src.common.domain.enums.workflow_rules import WorkflowAnalysisRunStatus
from src.common.domain.exceptions.workflow_rules import WorkflowAnalysisRunNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_analysis_run import WorkflowAnalysisRun
from src.workflows.domain.repositories.workflow_analysis_run import (
    WorkflowAnalysisRunRepository,
)
from src.workflows.presentation.workflows import workflow_id_for_run

logger = get_logger(__name__)


@dataclass
class CancelWorkflowAnalysisRun(UseCase):
    run_id: UUID
    tenant_id: UUID
    canceled_by: UUID | None
    run_repository: WorkflowAnalysisRunRepository
    temporal_client: TemporalClient

    async def execute(self) -> WorkflowAnalysisRun:
        run = await self.run_repository.find_by_id(self.run_id, self.tenant_id)
        if not run:
            raise WorkflowAnalysisRunNotFoundError(str(self.run_id))

        if not run.status.is_active:
            return run

        # Transitional state so the FE shows "cancelando..." while the
        # workflow drains in-flight activities.
        canceling = await self.run_repository.update_status(
            run_id=self.run_id,
            tenant_id=self.tenant_id,
            status=WorkflowAnalysisRunStatus.CANCELING,
            canceled_by=self.canceled_by,
        )

        handle = self.temporal_client.get_workflow_handle(workflow_id_for_run(self.run_id))
        try:
            await handle.signal(
                "cancel",  # name set by @workflow.signal on WorkflowAnalysisRunWorkflow.cancel
            )
        except RPCError:
            # Handle missing / closed — finalize directly so the run
            # doesn't get stuck in CANCELING.
            logger.warning(
                "analysis_run.cancel.signal_unavailable_fallback",
                run_id=str(self.run_id),
            )
            return await self.run_repository.update_status(
                run_id=self.run_id,
                tenant_id=self.tenant_id,
                status=WorkflowAnalysisRunStatus.CANCELED,
                canceled_by=self.canceled_by,
                completed=True,
            )

        return canceling
