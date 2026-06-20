"""WorkflowAnalysisRunWorkflow — orchestrates the evaluation of every
active rule against a case and drives the per-run SSE stream.

Lifecycle:
  1. `load_analysis_run_plan` → list[Combination]; workflow emits
     `RUN_STARTED` (with `totalEvaluations`).
  2. Fan out across `evaluate_rule_combination` activities with a
     bounded asyncio semaphore. After each completion we publish
     `RULE_RESULT_READY` and `RUN_PROGRESS`.
  3. `complete_analysis_run` runs the verdict aggregator + narrative
     synthesizer (which has its own SSE stream on the summary channel)
     and flips the run row to `COMPLETED`. Workflow publishes
     `RUN_COMPLETED`.
  4. On cancel signal: stop scheduling new evaluations, mark the run
     `CANCELED` via the status activity, publish `RUN_CANCELED`.
  5. On unexpected exception: mark the run `FAILED` via the status
     activity, publish `RUN_FAILED`.
"""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    import asyncio

    from src.common.domain.entities.workflows.analysis_run_processing import (
        AnalysisRunPlan,
        AnalysisRunWorkflowInput,
        CombinationPayload,
        CompleteAnalysisRunInput,
        EvaluateCombinationInput,
        EvaluateCombinationOutput,
        UpdateAnalysisRunStatusInput,
    )
    from src.common.domain.enums.workflow_rules import WorkflowAnalysisRunStatus
    from src.common.infrastructure.helpers.logger import get_logger
    from src.workflows.domain.events.workflow_analysis_run_event import (
        WorkflowAnalysisRunEvent,
    )

logger = get_logger(__name__)

DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=1),
    maximum_attempts=3,
)

# Activity names — kept here so other workflows (if added) can reference them.
LOAD_PLAN_ACTIVITY = "load_analysis_run_plan"
EVALUATE_COMBINATION_ACTIVITY = "evaluate_rule_combination"
UPDATE_STATUS_ACTIVITY = "update_analysis_run_status"
PUBLISH_EVENT_ACTIVITY = "publish_analysis_run_event"
COMPLETE_RUN_ACTIVITY = "complete_analysis_run"

# Bounded concurrency for rule evaluations. Chosen small so we don't
# hammer the LLM provider / DB connection pool when a workflow has many
# rules. Tunable via the workflow input later if needed.
EVAL_CONCURRENCY = 4


def workflow_id_for_run(run_id) -> str:
    """Stable Temporal workflow ID derived from the analysis run UUID.

    Used by both the starter (to launch) and the canceller (to look up
    the handle and signal). UUIDs are 32 hex chars — well under
    Temporal's id length limit.
    """
    return f"analysis-run-{run_id}"


@workflow.defn
class WorkflowAnalysisRunWorkflow:
    """Concurrent rule evaluation orchestrator with cancel + live SSE."""

    def __init__(self) -> None:
        self._cancel_requested: bool = False
        self._seq: int = 0
        self._completed: int = 0

    @workflow.signal
    async def cancel(self) -> None:
        self._cancel_requested = True

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    async def _publish(
        self,
        *,
        run_id,
        type: str,
        payload: dict,
    ) -> None:
        event = WorkflowAnalysisRunEvent(
            seq=self._next_seq(),
            ts=workflow.now(),
            payload=payload,
            type=type,  # type: ignore[arg-type]
            run_id=run_id,
        )
        await workflow.execute_activity(
            PUBLISH_EVENT_ACTIVITY,
            event,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

    async def _mark_status(
        self,
        *,
        run_id,
        tenant_id,
        status: WorkflowAnalysisRunStatus,
        error: str | None = None,
        completed: bool = False,
        canceled_by=None,
    ) -> None:
        await workflow.execute_activity(
            UPDATE_STATUS_ACTIVITY,
            UpdateAnalysisRunStatusInput(
                run_id=run_id,
                tenant_id=tenant_id,
                status=status,
                error=error,
                completed=completed,
                canceled_by=canceled_by,
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

    async def _evaluate_one(
        self,
        sem: asyncio.Semaphore,
        plan: AnalysisRunPlan,
        combo: CombinationPayload,
        total: int,
    ) -> EvaluateCombinationOutput | None:
        async with sem:
            if self._cancel_requested:
                return None
            try:
                output: EvaluateCombinationOutput = await workflow.execute_activity(
                    EVALUATE_COMBINATION_ACTIVITY,
                    EvaluateCombinationInput(
                        run_id=plan.run_id,
                        workflow_id=plan.workflow_id,
                        case_id=plan.case_id,
                        tenant_id=plan.tenant_id,
                        case_name=plan.case_name,
                        combination=combo,
                        providers=plan.providers,
                    ),
                    start_to_close_timeout=timedelta(minutes=10),
                    retry_policy=DEFAULT_RETRY_POLICY,
                    result_type=EvaluateCombinationOutput,
                )
            except Exception as exc:  # noqa: BLE001
                # The activity already persisted an ERRORED result via the
                # evaluator's internal try/except; if we land here the
                # failure is structural (rule missing, compilation gone,
                # DB blip). Log + surface a synthetic progress tick.
                # NOTE: use `error`, not `exception` — structlog's exception
                # formatter pulls in `rich.traceback` which touches `os.path`
                # and trips the workflow sandbox.
                logger.error(
                    "analysis_run.workflow.evaluate_activity_failed",
                    run_id=str(plan.run_id),
                    rule_id=str(combo.rule_id),
                    error=str(exc),
                )
                self._completed += 1
                await self._publish(
                    run_id=plan.run_id,
                    type="RUN_PROGRESS",
                    payload={"completed": self._completed, "total": total, "error": str(exc)},
                )
                return None

            self._completed += 1

            await self._publish(
                run_id=plan.run_id,
                type="RULE_RESULT_READY",
                payload=output.result_payload,
            )
            await self._publish(
                run_id=plan.run_id,
                type="RUN_PROGRESS",
                payload={"completed": self._completed, "total": total},
            )
            return output

    @workflow.run
    async def run(self, payload: AnalysisRunWorkflowInput) -> None:
        data = AnalysisRunWorkflowInput.model_validate(payload)

        try:
            plan: AnalysisRunPlan = await workflow.execute_activity(
                LOAD_PLAN_ACTIVITY,
                data,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=DEFAULT_RETRY_POLICY,
                result_type=AnalysisRunPlan,
            )
        except Exception as exc:  # noqa: BLE001
            await self._mark_status(
                run_id=data.run_id,
                tenant_id=data.tenant_id,
                status=WorkflowAnalysisRunStatus.FAILED,
                error=f"load_plan: {exc}",
                completed=True,
            )
            await self._publish(
                run_id=data.run_id,
                type="RUN_FAILED",
                payload={"error": f"load_plan: {exc}"},
            )
            raise

        total = len(plan.evaluations)

        await self._publish(
            run_id=plan.run_id,
            type="RUN_STARTED",
            payload={"runId": str(plan.run_id), "totalEvaluations": total},
        )

        if total == 0:
            await self._finalize(plan)
            return

        sem = asyncio.Semaphore(EVAL_CONCURRENCY)

        async def _run_all() -> None:
            await asyncio.gather(
                *(self._evaluate_one(sem, plan, combo, total) for combo in plan.evaluations)
            )

        gather_task = asyncio.create_task(_run_all())

        # Wait on a deterministic condition (Temporal-safe) instead of
        # asyncio.wait, which the workflow sandbox flags as non-deterministic.
        # The condition resolves as soon as either the gather completes or a
        # cancel signal flips `_cancel_requested`.
        await workflow.wait_condition(
            lambda: gather_task.done() or self._cancel_requested
        )

        if self._cancel_requested and not gather_task.done():
            # Cancel in-flight evaluations and let them unwind.
            gather_task.cancel()
            try:
                await gather_task
            except (asyncio.CancelledError, Exception):
                pass
            await self._finalize_canceled(plan)
            return

        try:
            gather_task.result()
        except Exception as exc:  # noqa: BLE001
            # gather only re-raises if a child raised past _evaluate_one
            # (which catches its own activity errors). Treat anything
            # leaking through here as a run-level failure.
            await self._mark_status(
                run_id=plan.run_id,
                tenant_id=plan.tenant_id,
                status=WorkflowAnalysisRunStatus.FAILED,
                error=str(exc),
                completed=True,
            )
            await self._publish(
                run_id=plan.run_id,
                type="RUN_FAILED",
                payload={"error": str(exc)},
            )
            raise

        if self._cancel_requested:
            await self._finalize_canceled(plan)
            return

        await self._finalize(plan)

    async def _finalize(self, plan: AnalysisRunPlan) -> None:
        try:
            await workflow.execute_activity(
                COMPLETE_RUN_ACTIVITY,
                CompleteAnalysisRunInput(run_id=plan.run_id, tenant_id=plan.tenant_id, providers=plan.providers),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=DEFAULT_RETRY_POLICY,
            )
        except Exception as exc:  # noqa: BLE001
            await self._mark_status(
                run_id=plan.run_id,
                tenant_id=plan.tenant_id,
                status=WorkflowAnalysisRunStatus.FAILED,
                error=f"complete: {exc}",
                completed=True,
            )
            await self._publish(
                run_id=plan.run_id,
                type="RUN_FAILED",
                payload={"error": f"complete: {exc}"},
            )
            raise ApplicationError(f"complete_analysis_run failed: {exc}", non_retryable=True) from exc

        await self._publish(
            run_id=plan.run_id,
            type="RUN_COMPLETED",
            payload={"runId": str(plan.run_id), "completed": self._completed},
        )

    async def _finalize_canceled(self, plan: AnalysisRunPlan) -> None:
        await self._mark_status(
            run_id=plan.run_id,
            tenant_id=plan.tenant_id,
            status=WorkflowAnalysisRunStatus.CANCELED,
            completed=True,
        )
        await self._publish(
            run_id=plan.run_id,
            type="RUN_CANCELED",
            payload={"runId": str(plan.run_id), "completed": self._completed},
        )
