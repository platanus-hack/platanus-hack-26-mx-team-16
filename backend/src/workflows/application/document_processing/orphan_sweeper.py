"""Reconciles `workflow_processing_jobs` rows whose Temporal workflow has ended
without the row being finalized.

Stuck rows can happen when:
- The worker crashed between the last `_checkpoint` and writing the
  terminal status.
- The runner (FastAPI side) lost connection during `handle.result()` so
  `mark_done` / `mark_failed` were never called.
- The workflow_processing_jobs row was committed but `start_workflow` failed
  (caught by the dispatch endpoint pre-commit guard, but defended here
  too).

The sweeper runs once on worker startup. For each non-terminal row it
queries Temporal:
- NOT_FOUND  → no workflow ever ran (or already retention-deleted) →
  mark_failed("orphaned: workflow not found").
- COMPLETED  → workflow finished cleanly → mark_done with a sweeper
  marker. The DocumentProcessingOutput is no longer accessible (the
  runner already missed it), so the summary is minimal.
- FAILED / CANCELED / TERMINATED / TIMED_OUT → mark_failed with the
  Temporal-side reason.
- Anything else (RUNNING) → leave alone; the workflow is still in
  flight and the live activities will finalize it.

Each reconciliation runs in its OWN repository context so a flush
failure on one document set doesn't poison the SQLAlchemy session for the next.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Callable

from temporalio.client import Client as TemporalClient
from temporalio.client import WorkflowExecutionStatus
from temporalio.service import RPCError, RPCStatusCode

from src.common.application.logging import get_logger
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.workflows.domain.repositories.workflow_processing_job_repository import (
    WorkflowProcessingJobRepository,
)

logger = get_logger(__name__)


_TERMINAL_TEMPORAL_STATUSES = {
    WorkflowExecutionStatus.COMPLETED,
    WorkflowExecutionStatus.FAILED,
    WorkflowExecutionStatus.CANCELED,
    WorkflowExecutionStatus.TERMINATED,
    WorkflowExecutionStatus.TIMED_OUT,
}


# Caller-provided async context manager that yields a fresh repository.
# Implementations are expected to commit on successful exit and rollback
# on exception, so each reconciliation runs in its own transaction.
RepositoryFactory = Callable[[], AbstractAsyncContextManager[WorkflowProcessingJobRepository]]


@dataclass
class OrphanedJobSweeper(UseCase):
    """Reconcile non-terminal `workflow_processing_jobs` rows whose Temporal
    workflow already ended (or never started)."""

    repository_factory: RepositoryFactory
    temporal_client: TemporalClient

    async def execute(self) -> dict:
        async with self.repository_factory() as repo:
            unfinished = await repo.list_unfinished()

        swept = {"checked": len(unfinished), "completed": 0, "failed": 0, "skipped": 0}

        for processing_job in unfinished:
            try:
                await self._reconcile(processing_job, swept)
            except RPCError as err:
                # Non-NOT_FOUND Temporal RPC errors (UNAVAILABLE,
                # DEADLINE_EXCEEDED, UNAUTHENTICATED, …) are typically
                # transient — log and keep going. The next worker boot
                # will pick this document set up again.
                swept["skipped"] += 1
                logger.warning(
                    "orphan_sweeper.rpc_error_skipped "
                    f"temporal_workflow_id={processing_job.temporal_workflow_id} status={err.status.name}"
                )
            except Exception:  # noqa: BLE001 — never let one bad row kill boot
                swept["skipped"] += 1
                logger.exception(
                    f"orphan_sweeper.unexpected_error_skipped temporal_workflow_id={processing_job.temporal_workflow_id}"
                )

        if swept["checked"] > 0:
            logger.info(f"orphan_sweeper.done {swept}")
        return swept

    async def _reconcile(self, processing_job: WorkflowProcessingJob, swept: dict) -> None:
        handle = self.temporal_client.get_workflow_handle(processing_job.temporal_workflow_id)
        try:
            desc = await handle.describe()
        except RPCError as err:
            if err.status == RPCStatusCode.NOT_FOUND:
                async with self.repository_factory() as repo:
                    await repo.mark_failed(processing_job.uuid, error="orphaned: workflow not found")
                swept["failed"] += 1
                logger.info(
                    f"orphan_sweeper.mark_failed reason=not_found temporal_workflow_id={processing_job.temporal_workflow_id}"
                )
                return
            raise

        status = desc.status
        if status not in _TERMINAL_TEMPORAL_STATUSES:
            # Workflow still running — leave it alone, normal activities
            # will finalize it.
            swept["skipped"] += 1
            return

        if status == WorkflowExecutionStatus.COMPLETED:
            async with self.repository_factory() as repo:
                await repo.mark_done(processing_job.uuid, summary={"swept": True})
            swept["completed"] += 1
            logger.info(
                f"orphan_sweeper.mark_done reason=completed temporal_workflow_id={processing_job.temporal_workflow_id}"
            )
        else:
            async with self.repository_factory() as repo:
                await repo.mark_failed(processing_job.uuid, error=f"orphaned: workflow ended {status.name}")
            swept["failed"] += 1
            logger.info(
                f"orphan_sweeper.mark_failed reason={status.name} temporal_workflow_id={processing_job.temporal_workflow_id}"
            )
