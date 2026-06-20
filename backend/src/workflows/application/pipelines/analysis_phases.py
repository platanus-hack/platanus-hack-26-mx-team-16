"""Fases case-scope del intérprete: analyze → output → deliver (E2 · plan §4.2).

- ``analyze`` (D3): arranca ``WorkflowAnalysisRunWorkflow`` como CHILD workflow
  y espera su resultado — conserva fan-out/SSE/cancel sin duplicar nada. El
  ``run_id`` es determinista (``workflow.uuid4``) para que los retries de la
  activity de creación sean idempotentes; un run activo ajeno se espera vía
  retry policy (uploads concurrentes al mismo caso se serializan).
- ``output``: ejecuta el spec case-output (outputs por documento + proyección
  x-source + síntesis LLM acotada) vía activity.
- ``deliver``: emite ``case.output.ready`` al outbox → destinos suscritos.
  ``case.failed`` se emite (best-effort) desde los caminos de fallo de
  analyze/output antes de propagar el error.

Los tres handlers SKIPEAN limpio cuando el run no tiene caso (uploads
STANDARD): la receta encadenada es válida para ambos mundos.
"""

from __future__ import annotations

import hashlib
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError, ChildWorkflowError
from temporalio.workflow import ParentClosePolicy

with workflow.unsafe.imports_passed_through():
    from src.common.domain.entities.workflows.analysis_run_processing import (
        AnalysisProviders,
        AnalysisRunWorkflowInput,
        BuildCaseOutputInput,
        BuildCaseOutputOutput,
        CreateAnalysisRunForPipelineInput,
        CreateAnalysisRunForPipelineOutput,
        DispatchCaseEventInput,
        MarkAnalysisRunFailedInput,
    )
    from src.common.domain.entities.workflows.case_runtime import (
        OpenQaAuditTaskInput,
        OpenQaAuditTaskOutput,
    )
    from src.common.domain.enums.pipelines import PhaseKind
    from src.common.domain.enums.webhooks import WebhookEventType
    from src.common.domain.enums.workflow_cases import WorkflowCaseStatus
    from src.workflows.application.pipelines.case_transitions import transition_case
    from src.workflows.application.pipelines.runtime import PipelineState, register_phase
    from src.workflows.domain.models.phase_configs import (
        AnalyzeConfig,
        DeliverConfig,
        OutputConfig,
        parse_duration,
    )
    from src.workflows.domain.models.policies import ActivationPolicy
    from src.workflows.presentation.workflows.analysis_run import workflow_id_for_run
    from src.workflows.presentation.workflows.base import DEFAULT_RETRY_POLICY

CREATE_ANALYSIS_RUN_ACTIVITY = "create_analysis_run"
MARK_ANALYSIS_RUN_FAILED_ACTIVITY = "mark_analysis_run_failed"
BUILD_CASE_OUTPUT_ACTIVITY = "build_case_output"
DISPATCH_CASE_EVENT_ACTIVITY = "dispatch_case_event"
OPEN_QA_AUDIT_TASK_ACTIVITY = "open_qa_audit_task"

ANALYSIS_CHILD_WORKFLOW = "WorkflowAnalysisRunWorkflow"


def _qa_sample_rate(state: PipelineState) -> float:
    """``ActivationPolicy.qa_sample_rate`` sellada con la versión (0 si ausente)."""
    raw = (state.scratch.get("policies") or {}).get("activation")
    if not raw:
        return 0.0
    return ActivationPolicy.model_validate(raw).qa_sample_rate


def _qa_sampled(case_id: str, qa_sample_rate: float) -> bool:
    """Muestreo determinista por case_id (sha256 — jamás random en workflow).

    Clave = case_id (no job_id) para que re-runs del mismo caso caigan igual
    (recon §3). Espejo de ``deterministic_sample`` de pause_phases."""
    if qa_sample_rate <= 0:
        return False
    bucket = (int(hashlib.sha256(case_id.encode()).hexdigest()[:8], 16) % 10**6) / 10**6
    return bucket < qa_sample_rate


# Espera máxima a que un run activo ajeno termine antes de fallar la fase.
ACTIVE_RUN_WAIT_TIMEOUT = timedelta(minutes=15)
_CREATE_RUN_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=0,  # acotado por schedule_to_close (la espera)
)


def _case_context(state: PipelineState):
    """(tenant_id, workflow_id, case_id) o None si la fase debe skipear."""
    data = state.data
    if not data.persist or data.case_id is None or data.tenant_id is None or data.workflow_id is None:
        return None
    return data.tenant_id, data.workflow_id, data.case_id


async def _dispatch_case_failed(state: PipelineState, run_id, code: str, message: str) -> None:
    """Best-effort: jamás enmascara el error original de la fase.

    E4 · diseño §1: el fallo terminal del run de caso también mueve el estado
    público a FAILED (best-effort, mismo contrato que el webhook)."""
    context = _case_context(state)
    if context is None:
        return
    tenant_id, workflow_id, case_id = context
    await transition_case(state, WorkflowCaseStatus.FAILED.value, reason=code)
    try:
        await workflow.execute_activity(
            DISPATCH_CASE_EVENT_ACTIVITY,
            DispatchCaseEventInput(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                case_id=case_id,
                run_id=run_id,
                event_type=WebhookEventType.CASE_FAILED.value,
                error={"code": code, "message": message[:500]},
            ),
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
    except Exception:  # noqa: BLE001
        workflow.logger.warning(f"pipeline.case_failed_dispatch_failed case_id={case_id}")


@register_phase(PhaseKind.ANALYZE.value, scope="case")
async def analyze(ctx, phase, state: PipelineState) -> None:
    context = _case_context(state)
    if context is None:
        workflow.logger.info(f"pipeline.analyze.skipped reason=no_case job_id={state.job_id}")
        state.put_artifact("analysis_run", {"skipped": True, "reason": "no_case"})
        return
    tenant_id, workflow_id, case_id = context
    cfg = AnalyzeConfig.model_validate(phase.config or {})
    # phases-config · H1/H2: overrides de provider + rule_set sellados en la config.
    # Se persisten en el artifact ``analysis_run`` (abajo) para que el re-analyze por
    # corrections (pause_phases._run_reanalysis) reproduzca la MISMA config —
    # sin esto las re-corridas revierten a env providers + TODAS las reglas.
    providers = AnalysisProviders(
        parser=cfg.parser_provider,
        reviewer=cfg.reviewer_provider,
        critic=cfg.critic_provider,
        synthesizer=cfg.synthesizer_provider,
    )

    # E4 · diseño §1: el caso entra a ANALYZING al arrancar la fase. Dos pasos
    # best-effort: PROCESSING primero levanta los casos data-only que llegan en
    # RECEIVING (DATA#); re-runs sobre casos COMPLETED se loggean y siguen.
    await transition_case(state, WorkflowCaseStatus.PROCESSING.value, reason="analyze.start")
    await transition_case(state, WorkflowCaseStatus.ANALYZING.value, reason="analyze.start")

    run_id = workflow.uuid4()
    await workflow.execute_activity(
        CREATE_ANALYSIS_RUN_ACTIVITY,
        CreateAnalysisRunForPipelineInput(
            run_id=run_id,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            case_id=case_id,
        ),
        result_type=CreateAnalysisRunForPipelineOutput,
        start_to_close_timeout=timedelta(seconds=30),
        schedule_to_close_timeout=parse_duration(cfg.active_run_wait_timeout, ACTIVE_RUN_WAIT_TIMEOUT),
        retry_policy=_CREATE_RUN_RETRY,
    )

    try:
        await workflow.execute_child_workflow(
            ANALYSIS_CHILD_WORKFLOW,
            AnalysisRunWorkflowInput(
                run_id=run_id,
                workflow_id=workflow_id,
                case_id=case_id,
                tenant_id=tenant_id,
                # phases-config · analyze: overrides de provider + rule_set sellados.
                providers=providers,
                rule_set=cfg.rule_set,
            ),
            id=workflow_id_for_run(run_id),
            # ABANDON: si el pipeline muere, el análisis sigue y cierra su fila
            # (su ciclo de vida vive en DB/SSE) — jamás filas RUNNING huérfanas
            # por un TERMINATE en cascada.
            parent_close_policy=ParentClosePolicy.ABANDON,
            # None ⇒ sin tope (comportamiento de hoy).
            execution_timeout=parse_duration(cfg.child_workflow_timeout, None),
        )
    except ChildWorkflowError as exc:
        cause = getattr(exc, "cause", None)
        message = str(cause or exc)
        await workflow.execute_activity(
            MARK_ANALYSIS_RUN_FAILED_ACTIVITY,
            MarkAnalysisRunFailedInput(run_id=run_id, tenant_id=tenant_id, error=message[:500]),
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
        await _dispatch_case_failed(state, run_id, "pipeline.analyze_failed", message)
        raise ApplicationError(
            f"analysis child workflow failed for case {case_id}: {message}",
            type="pipeline.analyze_failed",
            non_retryable=True,
        ) from exc

    # H1/H2: la config sellada viaja en el artifact para el re-analyze por corrections.
    state.put_artifact(
        "analysis_run",
        {"run_id": str(run_id), "providers": providers.model_dump(), "rule_set": cfg.rule_set},
    )


@register_phase(PhaseKind.OUTPUT.value, scope="case")
async def output(ctx, phase, state: PipelineState) -> None:
    context = _case_context(state)
    run_info = state.artifact("analysis_run") or {}
    if context is None or run_info.get("skipped") or not run_info.get("run_id"):
        workflow.logger.info(f"pipeline.output.skipped job_id={state.job_id}")
        state.put_artifact("case_output", {"skipped": True, "reason": "no_analysis_run"})
        return
    tenant_id, workflow_id, case_id = context
    run_id = run_info["run_id"]
    cfg = OutputConfig.model_validate(phase.config or {})

    try:
        result: BuildCaseOutputOutput = await workflow.execute_activity(
            BUILD_CASE_OUTPUT_ACTIVITY,
            BuildCaseOutputInput(
                run_id=run_id,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                case_id=case_id,
                synthesizer_provider=cfg.synthesizer_provider,
            ),
            result_type=BuildCaseOutputOutput,
            start_to_close_timeout=parse_duration(cfg.synthesis_timeout, timedelta(minutes=5)),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
    except ActivityError as exc:
        message = str(getattr(exc, "cause", None) or exc)
        await _dispatch_case_failed(state, run_id, "pipeline.output_failed", message)
        raise ApplicationError(
            f"case output failed for run {run_id}: {message}",
            type="pipeline.output_failed",
            non_retryable=True,
        ) from exc

    # Solo refs/metadata compactos en el artifact (límite 2 MiB de Temporal);
    # el output real vive en el summary del run.
    state.put_artifact("case_output", result.model_dump(mode="json"))


@register_phase(PhaseKind.DELIVER.value, scope="case")
async def deliver(ctx, phase, state: PipelineState) -> None:
    context = _case_context(state)
    case_output = state.artifact("case_output") or {}
    if context is None or case_output.get("skipped"):
        workflow.logger.info(f"pipeline.deliver.skipped job_id={state.job_id}")
        return
    tenant_id, workflow_id, case_id = context
    cfg = DeliverConfig.model_validate(phase.config or {})

    dispatched = await workflow.execute_activity(
        DISPATCH_CASE_EVENT_ACTIVITY,
        DispatchCaseEventInput(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            case_id=case_id,
            run_id=case_output.get("run_id"),
            event_type=WebhookEventType.CASE_OUTPUT_READY.value,
            channels=cfg.channels,
            payload_projection=cfg.payload_projection,
        ),
        start_to_close_timeout=parse_duration(cfg.dispatch_timeout, timedelta(seconds=60)),
        retry_policy=DEFAULT_RETRY_POLICY,
    )
    state.put_artifact("delivery", {"event": WebhookEventType.CASE_OUTPUT_READY.value, "dispatched": dispatched})
    # E4 · diseño §1: output entregado ⇒ el caso queda COMPLETED (best-effort;
    # transición al estado actual = no-op replay-safe).
    await transition_case(state, WorkflowCaseStatus.COMPLETED.value, reason="deliver")

    # E6 · §3: QA sampling post-COMPLETED. Fire-and-forget best-effort: si el
    # caso fue auto-aprobado y cae en la muestra, se abre una HumanTask kind=QA
    # (la activity verifica el universo "auto-aprobado" leyendo case_events). El
    # muestreo es determinista por case_id; rate=0 (default) ⇒ no-op total.
    # F1b: la config de la fase puede sobreescribir el rate sellado en la policy.
    qa_rate = cfg.qa_sample_rate if cfg.qa_sample_rate is not None else _qa_sample_rate(state)
    await _maybe_open_qa_audit(
        state,
        run_id=case_output.get("run_id"),
        qa_rate=qa_rate,
        qa_timeout=parse_duration(cfg.qa_audit_timeout, timedelta(seconds=30)),
    )


async def _maybe_open_qa_audit(state: PipelineState, *, run_id, qa_rate: float, qa_timeout) -> None:
    """Abre la auditoría QA sin pausar el run (fire-and-forget). Nunca tumba el
    run: un fallo de la activity sólo se loggea (el caso ya quedó COMPLETED)."""
    context = _case_context(state)
    if context is None:
        return
    tenant_id, workflow_id, case_id = context
    if not _qa_sampled(str(case_id), qa_rate):
        return
    try:
        await workflow.execute_activity(
            OPEN_QA_AUDIT_TASK_ACTIVITY,
            OpenQaAuditTaskInput(
                task_key=f"{workflow.info().workflow_id}:qa",
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                case_id=case_id,
                run_id=str(run_id) if run_id else None,
            ),
            result_type=OpenQaAuditTaskOutput,
            start_to_close_timeout=qa_timeout,
            retry_policy=DEFAULT_RETRY_POLICY,
        )
    except Exception:  # noqa: BLE001 — el QA jamás tumba un caso ya entregado
        workflow.logger.warning(f"pipeline.qa_audit_open_failed case_id={case_id}")
