"""Enrichment phase handler (F5 · A2 · extendido en E3 · plan §4.7).

``enrich`` calls a registered Tool through the deterministic connector (the LLM
never sees raw HTTP). The activity renders ``@slug.path`` / ``{{token}}`` args
and the URL template with case data, signs the request (HMAC, when configured),
validates schemas and persists the validated payload as a virtual
``WorkflowDocument`` (source=TOOL) — rules then see it as ``@slug`` for free.

Phase config contract::

    {
      "tool": "lookup_poliza",            # required: ToolDefinition.name
      "args": {"q": "@oficio.numero"},    # optional: rule-syntax templates
      "output_doc_type_slug": "poliza",   # optional: defaults to tool name
      "on_failure": "review",             # review (default) | continue | fail
      "persist_degraded": false,          # optional: persist partial payloads
      "output_key": "poliza"              # optional: scratch key (compat)
    }

``scratch['enrichment'][output_key]`` is kept for ``when``-predicate compat in
addition to the virtual document. Failure semantics:

- config errors (``pipeline.enrich_config_error`` from the activity, or an
  invalid ``on_failure`` value) fail the pipeline — never the on_failure path;
- ``continue``: log + degraded marker in scratch, the run goes on;
- ``fail``: best-effort ``case.failed`` dispatch, then a non-retryable
  ``ApplicationError`` type ``pipeline.enrich_failed``;
- ``review`` (default): opens a HumanTask (approval / internal_queue, visible
  in the /review queue) WITHOUT pausing the run — in E3 there is no state
  machine for enrich reviews; the task is a flag for operators, the pipeline
  continues degraded.

Retries are unified (plan §4.7 gotcha): the connector already does up to 3 HTTP
attempts internally, so the activity runs with ``maximum_attempts=1`` and a 60s
``start_to_close`` — never 2x3 calls.
"""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

with workflow.unsafe.imports_passed_through():
    from src.common.domain.entities.workflows.analysis_run_processing import (
        DispatchCaseEventInput,
    )
    from src.common.domain.entities.workflows.human_task_io import (
        CreateHumanTaskInput,
        CreateHumanTaskOutput,
    )
    from src.common.domain.entities.workflows.tool_lookup import (
        ENRICH_CONFIG_ERROR_TYPE,
        ToolLookupInput,
        ToolLookupOutput,
    )
    from src.common.domain.enums.processing_job_events import ProcessingJobEventType, JobStatus
    from src.common.domain.enums.human_tasks import HumanTaskAssigneeMode, HumanTaskKind
    from src.common.domain.enums.pipelines import PhaseKind
    from src.common.domain.enums.tools import ToolCallStatus
    from src.common.domain.enums.webhooks import WebhookEventType
    from src.workflows.application.pipelines.runtime import PipelineState, register_phase
    from src.workflows.presentation.workflows.base import DEFAULT_RETRY_POLICY

TOOL_LOOKUP_ACTIVITY = "tool_lookup"
CREATE_HUMAN_TASK_ACTIVITY = "create_human_task"
DISPATCH_CASE_EVENT_ACTIVITY = "dispatch_case_event"

ENRICH_FAILED_TYPE = "pipeline.enrich_failed"
_ON_FAILURE_MODES = {"review", "continue", "fail"}

# Plan §4.7: "retries=3" vive DENTRO del connector (3 intentos HTTP). Una sola
# ejecución de la activity evita la doble capa (gotcha de las 6 llamadas).
_ENRICH_RETRY = RetryPolicy(maximum_attempts=1)


@register_phase(PhaseKind.ENRICH.value, scope="case")
async def enrich(ctx, phase, state: PipelineState) -> None:
    cfg = phase.config or {}
    tool_name = cfg.get("tool")
    if not tool_name or state.data.tenant_id is None:
        return
    on_failure = cfg.get("on_failure", "review")
    if on_failure not in _ON_FAILURE_MODES:
        msg = (
            f"enrich phase '{phase.id}': invalid on_failure {on_failure!r} "
            f"(expected one of {sorted(_ON_FAILURE_MODES)})"
        )
        raise ApplicationError(msg, type=ENRICH_CONFIG_ERROR_TYPE, non_retryable=True)
    output_key = cfg.get("output_key") or tool_name

    try:
        result: ToolLookupOutput = await workflow.execute_activity(
            TOOL_LOOKUP_ACTIVITY,
            ToolLookupInput(
                tenant_id=state.data.tenant_id,
                tool_name=tool_name,
                args=cfg.get("args") or {},
                case_id=state.data.case_id,
                workflow_id=state.data.workflow_id,
                output_doc_type_slug=cfg.get("output_doc_type_slug"),
                persist_degraded=bool(cfg.get("persist_degraded", False)),
            ),
            result_type=ToolLookupOutput,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=_ENRICH_RETRY,
        )
    except ActivityError as exc:
        cause = getattr(exc, "cause", None)
        if isinstance(cause, ApplicationError) and cause.type == ENRICH_CONFIG_ERROR_TYPE:
            # Error de configuración: jamás on_failure — el pipeline muere.
            message = str(cause)
            await _dispatch_enrich_failed(state, ENRICH_CONFIG_ERROR_TYPE, message)
            msg = f"enrich '{tool_name}' is misconfigured: {message}"
            raise ApplicationError(msg, type=ENRICH_CONFIG_ERROR_TYPE, non_retryable=True) from exc
        # Infra/timeout tras el único intento ⇒ tratar como degradado (on_failure).
        result = ToolLookupOutput(
            status=ToolCallStatus.DEGRADED,
            error=f"activity_failed: {str(cause or exc)[:200]}",
        )

    degraded = result.status != ToolCallStatus.OK
    entry = {
        "status": result.status.value,
        "data": result.data,
        "error": result.error,
        "document_id": str(result.document_id) if result.document_id else None,
    }
    if degraded:
        entry["degraded"] = True
    state.scratch.setdefault("enrichment", {})[output_key] = entry

    applied: str | None = None
    if degraded:
        applied = on_failure
        if on_failure == "fail":
            message = result.error or "tool lookup degraded"
            await _dispatch_enrich_failed(state, ENRICH_FAILED_TYPE, message)
            msg = f"enrich '{tool_name}' failed: {message}"
            raise ApplicationError(msg, type=ENRICH_FAILED_TYPE, non_retryable=True)
        if on_failure == "review":
            await _open_review_task(phase, state, tool_name, result)
        else:  # continue
            workflow.logger.warning(
                f"pipeline.enrich.degraded tool={tool_name} error={result.error} mode=continue"
            )

    await ctx._checkpoint(
        state.data,
        type=ProcessingJobEventType.STEP_COMPLETED,
        payload={
            "step": PhaseKind.ENRICH.value,
            "tool": tool_name,
            "status": result.status.value,
            "document_id": entry["document_id"],
            "error": result.error,
            "on_failure": applied,
        },
        job_status=JobStatus.PROCESSING,
    )


async def _dispatch_enrich_failed(state: PipelineState, code: str, message: str) -> None:
    """Best-effort ``case.failed`` ANTES de propagar — clona el patrón de
    ``analysis_phases._dispatch_case_failed`` (jamás enmascara el error)."""
    data = state.data
    if not data.persist or data.case_id is None or data.tenant_id is None or data.workflow_id is None:
        return
    try:
        await workflow.execute_activity(
            DISPATCH_CASE_EVENT_ACTIVITY,
            DispatchCaseEventInput(
                tenant_id=data.tenant_id,
                workflow_id=data.workflow_id,
                case_id=data.case_id,
                run_id=None,
                event_type=WebhookEventType.CASE_FAILED.value,
                error={"code": code, "message": message[:500]},
            ),
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
    except Exception:  # jamás enmascarar el error original
        workflow.logger.warning(f"pipeline.enrich.case_failed_dispatch_failed case_id={data.case_id}")


async def _open_review_task(phase, state: PipelineState, tool_name: str, result) -> None:
    """``on_failure: review`` — opens the task and CONTINUES (no durable wait).

    E3: no enrich state machine yet; the task lands in the /review internal
    queue so an operator sees the degraded enrichment. Reuses the
    ``create_human_task`` activity (idempotent by task_key across replays).
    """
    run_id = workflow.info().workflow_id
    task_key = f"{run_id}:{phase.id}:enrich_review"
    created: CreateHumanTaskOutput = await workflow.execute_activity(
        CREATE_HUMAN_TASK_ACTIVITY,
        CreateHumanTaskInput(
            task_key=task_key,
            tenant_id=state.data.tenant_id,
            kind=HumanTaskKind.APPROVAL,
            assignee_mode=HumanTaskAssigneeMode.INTERNAL_QUEUE,
            workflow_id=state.data.workflow_id,
            case_id=state.data.case_id,
            pipeline_run_id=run_id,
            payload={
                "tool": tool_name,
                "error": result.error,
                "case_id": str(state.data.case_id) if state.data.case_id else None,
            },
        ),
        result_type=CreateHumanTaskOutput,
        start_to_close_timeout=timedelta(seconds=30),
        retry_policy=DEFAULT_RETRY_POLICY,
    )
    state.scratch.setdefault("enrichment_reviews", {})[phase.id] = {
        "task_key": task_key,
        "task_id": str(created.task_id),
    }
