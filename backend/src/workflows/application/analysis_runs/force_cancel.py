"""Force-cancel a WorkflowAnalysisRun that is stuck in CANCELING.

Used as the escape hatch when the Temporal workflow handle has gone
away (worker crash, mid-cancel restart, signal lost) and the row
remains in `CANCELING`, blocking the user from launching a new run for
the case.

This bypasses the cooperative cancel signal: it flips the row to
`CANCELED` directly and best-effort-terminates the workflow handle so
no zombie execution keeps running in the background. Termination
failures are logged and swallowed — the whole point of this entry
point is that the handle might already be gone.

Publishes `RUN_CANCELED` on the per-run SSE channel so any open EventSource
on the FE finalizes cleanly instead of waiting forever.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from temporalio.client import Client as TemporalClient
from temporalio.service import RPCError

from src.common.application.logging import get_logger
from src.common.domain.enums.workflow_rules import WorkflowAnalysisRunStatus
from src.common.domain.exceptions.workflow_rules import WorkflowAnalysisRunNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_analysis_run import WorkflowAnalysisRun
from src.common.infrastructure.event_publisher import EventPublisher
from src.workflows.domain.events.workflow_analysis_run_event import (
    WorkflowAnalysisRunEvent,
)
from src.workflows.domain.repositories.workflow_analysis_run import (
    WorkflowAnalysisRunRepository,
)
from src.workflows.presentation.workflows import workflow_id_for_run

logger = get_logger(__name__)


@dataclass
class ForceCancelWorkflowAnalysisRun(UseCase):
    run_id: UUID
    tenant_id: UUID
    canceled_by: UUID | None
    run_repository: WorkflowAnalysisRunRepository
    temporal_client: TemporalClient
    event_publisher: EventPublisher

    async def execute(self) -> WorkflowAnalysisRun:
        run = await self.run_repository.find_by_id(self.run_id, self.tenant_id)
        if not run:
            raise WorkflowAnalysisRunNotFoundError(str(self.run_id))

        # Already terminal — nothing to force.
        if run.status.is_terminal:
            return run

        # Best-effort Temporal termination. If the handle is gone we
        # don't care; the DB flip below is what actually unblocks the FE.
        handle = self.temporal_client.get_workflow_handle(workflow_id_for_run(self.run_id))
        try:
            await handle.terminate(reason="force-cancel from API")
        except RPCError as exc:
            logger.warning(
                "analysis_run.force_cancel.terminate_failed",
                run_id=str(self.run_id),
                reason=str(exc),
            )

        canceled = await self.run_repository.update_status(
            run_id=self.run_id,
            tenant_id=self.tenant_id,
            status=WorkflowAnalysisRunStatus.CANCELED,
            canceled_by=self.canceled_by,
            completed=True,
        )

        # Publish a terminal event so any open SSE subscriber on the FE
        # closes cleanly. Best-effort: failure here doesn't roll back the
        # cancellation — the FE will pick up the canceled status on its
        # next list/get poll if SSE doesn't deliver.
        try:
            await self.event_publisher.publish(
                WorkflowAnalysisRunEvent(
                    seq=0,
                    ts=datetime.now(UTC),
                    payload={
                        "runId": str(self.run_id),
                        "forced": True,
                    },
                    type="RUN_CANCELED",
                    run_id=self.run_id,
                )
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "analysis_run.force_cancel.publish_failed",
                run_id=str(self.run_id),
            )

        return canceled
