"""Durable pause phase handlers (F6 · evolucionados en E4 · diseño §4).

- ``await_documents``: loop durable de completitud — evalúa la
  ``CompletenessPolicy`` sellada contra los docs EXTRACTED del caso y espera
  señales ``case_docs_changed``/``case_ready`` hasta proceder; al proceder
  marca el caso ready (RECEIVING→PROCESSING + case_event ``ready``).
- ``extraction_gate`` evalúa la ActivationPolicy y, ante baja confianza, enruta
  (mutuamente excluyente) a aclaración (HumanTask EXTERNAL_CALLBACK + webhook
  ``case.needs_clarification`` + NEEDS_CLARIFICATION) o a revisión de staff;
  ``await_clarification`` queda como pausa de aclaración incondicional (F6) y
  ``human_review`` cubre el gate de aprobación post-analyze (mandatory | by_exception).
- Sin caso (runs sueltos / sin gate items) los handlers conservan el
  comportamiento F6 original (``_open_and_wait``): abrir task genérica,
  checkpoint y bloquear en ``task_resolved``.

Importing this module registers the handlers.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import timedelta

from temporalio import workflow
from temporalio.exceptions import ApplicationError
from temporalio.workflow import ParentClosePolicy

with workflow.unsafe.imports_passed_through():
    from src.common.domain.entities.workflows.case_runtime import (
        BuildStageGateItemsInput,
        BuildStageGateItemsOutput,
        CheckBlockingResultsInput,
        CheckBlockingResultsOutput,
        EvaluateActivationGateInput,
        EvaluateActivationGateOutput,
        EvaluateCaseCompletenessInput,
        EvaluateCaseCompletenessOutput,
        MarkCaseReadyInput,
        MarkCaseReadyOutput,
        OpenApprovalTaskInput,
        OpenCaseTaskOutput,
        OpenClarificationTaskInput,
    )
    from src.common.domain.entities.workflows.human_task_io import (
        CreateHumanTaskInput,
        CreateHumanTaskOutput,
    )
    from src.common.domain.entities.workflows.analysis_run_processing import (
        AnalysisProviders,
        AnalysisRunWorkflowInput,
        CreateAnalysisRunForPipelineInput,
        CreateAnalysisRunForPipelineOutput,
        DispatchCaseEventInput,
        MarkAnalysisRunFailedInput,
    )
    from src.common.domain.enums.processing_job_events import ProcessingJobEventType, JobStatus
    from src.common.domain.enums.human_tasks import HumanTaskAssigneeMode, HumanTaskKind
    from src.common.domain.enums.pipelines import PhaseKind
    from src.common.domain.enums.webhooks import WebhookEventType
    from src.common.domain.enums.workflow_cases import WorkflowCaseStatus
    from src.workflows.domain.models.phase_configs import (
        AwaitClarificationConfig,
        ExtractionGateConfig,
        HumanReviewConfig,
        parse_duration,
    )
    from src.workflows.domain.services.approval_quorum import (
        evaluate_quorum,
        quorum_pool_size,
        tally_votes,
    )
    from src.workflows.application.pipelines.analysis_phases import (
        ACTIVE_RUN_WAIT_TIMEOUT,
        ANALYSIS_CHILD_WORKFLOW,
        CREATE_ANALYSIS_RUN_ACTIVITY,
        MARK_ANALYSIS_RUN_FAILED_ACTIVITY,
        _CREATE_RUN_RETRY,
    )
    from src.workflows.application.pipelines.case_transitions import (
        append_case_event,
        case_context,
        transition_case,
    )
    from src.workflows.application.pipelines.runtime import PipelineState, register_phase
    from src.workflows.domain.models.policies import ActivationPolicy, CompletenessPolicy
    from src.workflows.presentation.workflows.analysis_run import workflow_id_for_run
    from src.workflows.presentation.workflows.base import DEFAULT_RETRY_POLICY

CREATE_HUMAN_TASK_ACTIVITY = "create_human_task"
EVALUATE_CASE_COMPLETENESS_ACTIVITY = "evaluate_case_completeness"
MARK_CASE_READY_ACTIVITY = "mark_case_ready"
OPEN_CLARIFICATION_TASK_ACTIVITY = "open_clarification_task"
OPEN_APPROVAL_TASK_ACTIVITY = "open_approval_task"
EVALUATE_ACTIVATION_GATE_ACTIVITY = "evaluate_activation_gate"
CHECK_BLOCKING_RESULTS_ACTIVITY = "check_blocking_results"
BUILD_STAGE_GATE_ITEMS_ACTIVITY = "build_stage_gate_items"
DISPATCH_CASE_EVENT_ACTIVITY = "dispatch_case_event"

CLARIFICATION_RESOLVED_EVENT = "clarification.resolved"
CLARIFICATION_ESCALATED_EVENT = "clarification.escalated"
REVIEW_SKIPPED_EVENT = "review.skipped"
REVIEW_APPROVED_EVENT = "review.approved"
REVIEW_REJECTED_EVENT = "review.rejected"
ANALYSIS_RERUN_EVENT = "analysis.rerun"

# E5 · §3.1: revisión multinivel — estado y audiencia por stage.
REVIEW_STAGE_STATUS = {
    "review_l1": WorkflowCaseStatus.REVIEW_L1.value,
    "review_l2": WorkflowCaseStatus.REVIEW_L2.value,
}
STAGE_AUDIENCE = {"review_l1": "doxiq_analyst", "review_l2": "tenant_analyst"}
# Filtro Rossum: el L2 no re-presenta lo ya verificado por L1 (level >= 1).
STAGE_EXCLUDE_VERIFIED_LEVEL = {"review_l1": None, "review_l2": 1}


# ─── helpers ─────────────────────────────────────────────────────────────────


def _task_key(phase) -> str:
    return f"{workflow.info().workflow_id}:{phase.id}"


def _activation_policy(state: PipelineState) -> ActivationPolicy:
    raw = (state.scratch.get("policies") or {}).get("activation")
    if raw:
        return ActivationPolicy.model_validate(raw)
    return ActivationPolicy()


def _completeness_policy(state: PipelineState) -> CompletenessPolicy | None:
    raw = (state.scratch.get("policies") or {}).get("completeness")
    if raw:
        return CompletenessPolicy.model_validate(raw)
    return None


def deterministic_sample(job_id: str, sample_rate: float) -> bool:
    """Sampling determinista por job_id (sha256 — JAMÁS random() en workflow)."""
    if sample_rate <= 0:
        return False
    bucket = (int(hashlib.sha256(job_id.encode()).hexdigest()[:8], 16) % 10**6) / 10**6
    return bucket < sample_rate


async def _dispatch_case_task_event(state: PipelineState, *, event_type: str, task_id, payload: dict) -> None:
    """Webhook ``case.needs_*`` best-effort (idempotente por case+task)."""
    context = case_context(state)
    if context is None:
        return
    tenant_id, workflow_id, case_id = context
    try:
        await workflow.execute_activity(
            DISPATCH_CASE_EVENT_ACTIVITY,
            DispatchCaseEventInput(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                case_id=case_id,
                event_type=event_type,
                task_id=task_id,
                payload=payload,
            ),
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
    except Exception:  # noqa: BLE001 — el webhook jamás tumba el run
        workflow.logger.warning(f"pipeline.case_task_event_failed case_id={case_id} type={event_type}")


async def _open_and_wait(
    ctx,
    phase,
    state: PipelineState,
    *,
    kind: HumanTaskKind,
    default_assignee: HumanTaskAssigneeMode,
    event_name: str,
) -> None:
    """Flujo F6 original: task genérica + checkpoint + bloqueo durable."""
    data = state.data
    if data.tenant_id is None:
        return  # cannot open a task without a tenant
    # Fallback compartido por await_clarification y human_review: ambos modelos
    # exponen assignee_mode/audience/payload idénticos ⇒ se elige por kind.
    cfg_model = HumanReviewConfig if phase.kind is PhaseKind.HUMAN_REVIEW else AwaitClarificationConfig
    cfg = cfg_model.model_validate(phase.config or {})
    run_id = workflow.info().workflow_id
    task_key = f"{run_id}:{phase.id}"

    created: CreateHumanTaskOutput = await workflow.execute_activity(
        CREATE_HUMAN_TASK_ACTIVITY,
        CreateHumanTaskInput(
            task_key=task_key,
            tenant_id=data.tenant_id,
            kind=kind,
            assignee_mode=cfg.assignee_mode or default_assignee,
            audience=cfg.audience,
            workflow_id=data.workflow_id,
            case_id=data.case_id,
            pipeline_run_id=run_id,
            payload=cfg.payload or {},
        ),
        result_type=CreateHumanTaskOutput,
        start_to_close_timeout=timedelta(seconds=30),
        retry_policy=DEFAULT_RETRY_POLICY,
    )

    await ctx._checkpoint(
        data,
        type=ProcessingJobEventType.STEP_COMPLETED,
        payload={
            "step": phase.kind.value,
            "event": event_name,
            "task_key": task_key,
            "task_id": str(created.task_id),
            "audience": cfg.audience,
        },
        job_status=JobStatus.PROCESSING,
    )

    resolution = await ctx.wait_for_task(task_key)
    state.scratch.setdefault("resolutions", {})[phase.id] = resolution


# ─── await_documents (E4 · diseño §4) ────────────────────────────────────────


@register_phase(PhaseKind.AWAIT_DOCUMENTS.value, scope="case")
async def await_documents(ctx, phase, state: PipelineState) -> None:
    """Loop durable: evaluar completitud → (proceder | esperar señal) → ready.

    Procede si ``satisfied && (auto_ready || ready solicitado)`` o si llegó
    ``case_ready {force: true}``. Sin policy / required_types vacío:
    satisfied=True pero espera el ready explícito salvo ``auto_ready``.
    """
    context = case_context(state)
    if context is None:
        workflow.logger.info(f"pipeline.await_documents.skipped reason=no_case job_id={state.job_id}")
        return
    tenant_id, _workflow_id, case_id = context

    policy = _completeness_policy(state)
    auto_ready = bool(policy.auto_ready) if policy else False

    result: EvaluateCaseCompletenessOutput
    forced = False
    child_auto = False
    while True:
        # E5 · fan-out (§2.2): el run document-scope partió el caso —
        # el padre sale del wait, queda PROCESSING y salta el resto de las
        # fases case-scope (el case_event ``case.split`` ya fue escrito).
        if bool(getattr(ctx, "_case_split", False)):
            await transition_case(state, WorkflowCaseStatus.PROCESSING.value, reason="case.split")
            state.scratch["split"] = True
            state.put_artifact("await_documents", {"split": True})
            state.terminated = True
            return
        docs_seen, ready_seen = ctx.case_signal_marks()
        result = await workflow.execute_activity(
            EVALUATE_CASE_COMPLETENESS_ACTIVITY,
            EvaluateCaseCompletenessInput(tenant_id=tenant_id, case_id=case_id),
            result_type=EvaluateCaseCompletenessOutput,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
        # E5 · fan-out (§2.2): un child nace completo — auto-ready al primer
        # ``case_docs_changed`` (la CompletenessPolicy está diseñada para el padre).
        if result.is_child and getattr(ctx, "_case_docs_changed_count", 0) > 0:
            child_auto = True
            forced = False
            break
        ready_requested = bool(getattr(ctx, "_case_ready_requested", False))
        force = bool(getattr(ctx, "_case_ready_force", False))
        if result.satisfied and (auto_ready or ready_requested):
            forced = False
            break
        if ready_requested and force:
            forced = not result.satisfied
            break
        await ctx.wait_for_case_signal(docs_seen, ready_seen)

    auto = child_auto or (result.satisfied and auto_ready and not bool(getattr(ctx, "_case_ready_requested", False)))
    marked: MarkCaseReadyOutput = await workflow.execute_activity(
        MARK_CASE_READY_ACTIVITY,
        MarkCaseReadyInput(tenant_id=tenant_id, case_id=case_id, forced=forced, auto=auto),
        result_type=MarkCaseReadyOutput,
        start_to_close_timeout=timedelta(seconds=30),
        retry_policy=DEFAULT_RETRY_POLICY,
    )
    state.put_artifact(
        "await_documents",
        {
            "satisfied": result.satisfied,
            "forced": forced,
            "auto": auto,
            "ready_at": marked.ready_at,
        },
    )


# ─── await_clarification (E4 · §4.5) ─────────────────────────────────────────


async def _on_clarification_timeout(ctx, phase, state: PipelineState, task_key: str, cfg, opened) -> dict:
    """G4 · on_timeout de await_clarification. ``fail`` ⇒ caso FAILED + error
    terminal; ``escalate`` ⇒ case_event ``clarification.escalated`` + desbloquea;
    cualquier otro (incl. None) ⇒ auto_resolve (desbloquea sin datos)."""
    action = cfg.on_timeout or "fail"
    if action == "fail":
        await transition_case(state, WorkflowCaseStatus.FAILED.value, reason=f"{phase.id}.timeout")
        raise ApplicationError(
            f"clarification timed out for phase {phase.id}",
            type="pipeline.clarification_timeout",
            non_retryable=True,
        )
    if action == "escalate":
        await append_case_event(
            state,
            CLARIFICATION_ESCALATED_EVENT,
            {"taskId": str(opened.task_id)},
            dedupe_key=f"{task_key}:{CLARIFICATION_ESCALATED_EVENT}",
        )
        return {"escalated": True}
    return {"autoResolved": True}


@register_phase(PhaseKind.AWAIT_CLARIFICATION.value, scope="case")
async def await_clarification(ctx, phase, state: PipelineState) -> None:
    """Pausa de aclaración incondicional (F6 standalone). La aclaración gateada por
    confianza la maneja ``extraction_gate``; esta fase es para pipelines que piden
    aclaración a un humano/sistema sin compuerta de confianza."""
    await _open_and_wait(
        ctx,
        phase,
        state,
        kind=HumanTaskKind.CLARIFICATION,
        default_assignee=HumanTaskAssigneeMode.EXTERNAL_CALLBACK,
        event_name="needs_clarification",
    )


# ─── extraction_gate (consolida confidence_gate + clarify + review-gate) ─────


@register_phase(PhaseKind.EXTRACTION_GATE.value, scope="case")
async def extraction_gate(ctx, phase, state: PipelineState) -> None:
    """Compuerta de extracción PRE-analyze (E4 consolidado).

    Evalúa la ``ActivationPolicy`` sellada y, ante baja confianza, enruta el caso
    (mutuamente excluyente) por ``on_low_confidence``: ``clarify`` (tarea al
    remitente) o ``review`` (cola de staff). Sin breach ⇒ continue. La rama vive
    AQUÍ (branch-inside-phase) — sin ``scratch["gate"]``. Reemplaza la tripleta
    confidence_gate + await_clarification(gate) + review_gate.
    """
    context = case_context(state)
    policy_raw = (state.scratch.get("policies") or {}).get("activation")
    if context is None or not policy_raw:
        # Run suelto o sin policy sellada ⇒ nada que enrutar (no-op limpio).
        return
    tenant_id, _workflow_id, case_id = context
    policy = ActivationPolicy.model_validate(policy_raw)

    result: EvaluateActivationGateOutput = await workflow.execute_activity(
        EVALUATE_ACTIVATION_GATE_ACTIVITY,
        EvaluateActivationGateInput(
            tenant_id=tenant_id,
            case_id=case_id,
            activation_policy=policy_raw,
        ),
        result_type=EvaluateActivationGateOutput,
        start_to_close_timeout=timedelta(seconds=60),
        retry_policy=DEFAULT_RETRY_POLICY,
    )
    items = result.items
    if not items:
        await ctx._checkpoint(
            state.data,
            type=ProcessingJobEventType.STEP_COMPLETED,
            payload={"step": phase.kind.value, "decision": "continue", "flagged": 0},
            job_status=JobStatus.PROCESSING,
        )
        return

    if policy.on_low_confidence == "review":
        await _extraction_gate_review(ctx, phase, state, items)
    else:
        await _extraction_gate_clarify(ctx, phase, state, items)


async def _extraction_gate_clarify(ctx, phase, state: PipelineState, items: list[dict]) -> None:
    """Rama clarify: abre un HumanTask al remitente (EXTERNAL_CALLBACK) + webhook
    ``case.needs_clarification`` + pausa NEEDS_CLARIFICATION; los ``items`` (breaches)
    se pasan explícitos (sin ``scratch["gate"]``)."""
    tenant_id, workflow_id, case_id = case_context(state)
    cfg = ExtractionGateConfig.model_validate(phase.config or {})
    task_key = _task_key(phase)
    run_id = workflow.info().workflow_id

    opened: OpenCaseTaskOutput = await workflow.execute_activity(
        OPEN_CLARIFICATION_TASK_ACTIVITY,
        OpenClarificationTaskInput(
            task_key=task_key,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            case_id=case_id,
            pipeline_run_id=run_id,
            items=items,
            expires_in_hours=cfg.expires_in_hours,
            audience=cfg.audience,
        ),
        result_type=OpenCaseTaskOutput,
        start_to_close_timeout=timedelta(seconds=30),
        retry_policy=DEFAULT_RETRY_POLICY,
    )

    await transition_case(state, WorkflowCaseStatus.NEEDS_CLARIFICATION.value, reason=phase.id)
    await _dispatch_case_task_event(
        state,
        event_type=WebhookEventType.CASE_NEEDS_CLARIFICATION.value,
        task_id=opened.task_id,
        payload=opened.payload,
    )
    await ctx._checkpoint(
        state.data,
        type=ProcessingJobEventType.STEP_COMPLETED,
        payload={
            "step": phase.kind.value,
            "event": "needs_clarification",
            "task_key": task_key,
            "task_id": str(opened.task_id),
            "items": len(items),
        },
        job_status=JobStatus.PROCESSING,
    )

    timeout_td = parse_duration(cfg.resolution_timeout, None) if cfg.resolution_timeout else None
    if timeout_td is None:
        resolution = await ctx.wait_for_task(task_key)
    else:
        try:
            await workflow.wait_condition(lambda: task_key in ctx._resolved_tasks, timeout=timeout_td)
            resolution = ctx._resolved_tasks[task_key]
        except asyncio.TimeoutError:
            resolution = await _on_clarification_timeout(ctx, phase, state, task_key, cfg, opened)
    state.scratch.setdefault("resolutions", {})[phase.id] = resolution

    await append_case_event(
        state,
        CLARIFICATION_RESOLVED_EVENT,
        {"taskId": str(opened.task_id)},
        dedupe_key=f"{task_key}:{CLARIFICATION_RESOLVED_EVENT}",
    )
    await transition_case(state, WorkflowCaseStatus.PROCESSING.value, reason=f"{phase.id}.resolved")


async def _extraction_gate_review(ctx, phase, state: PipelineState, items: list[dict]) -> None:
    """Rama review: abre una tarea APPROVAL (trigger ``gate_review``) a la cola de
    staff + pausa NEEDS_REVIEW; un rechazo termina el caso (REJECTED + terminated).
    Los ``items`` (breaches) se pasan explícitos."""
    tenant_id, workflow_id, case_id = case_context(state)
    cfg = ExtractionGateConfig.model_validate(phase.config or {})
    task_key = _task_key(phase)

    opened: OpenCaseTaskOutput = await workflow.execute_activity(
        OPEN_APPROVAL_TASK_ACTIVITY,
        OpenApprovalTaskInput(
            task_key=task_key,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            case_id=case_id,
            pipeline_run_id=workflow.info().workflow_id,
            trigger="gate_review",
            gate_items=items,
            audience=cfg.review_audience,
        ),
        result_type=OpenCaseTaskOutput,
        start_to_close_timeout=timedelta(seconds=30),
        retry_policy=DEFAULT_RETRY_POLICY,
    )

    await transition_case(state, WorkflowCaseStatus.NEEDS_REVIEW.value, reason=phase.id)
    await _dispatch_case_task_event(
        state,
        event_type=WebhookEventType.CASE_NEEDS_REVIEW.value,
        task_id=opened.task_id,
        payload=opened.payload,
    )
    await ctx._checkpoint(
        state.data,
        type=ProcessingJobEventType.STEP_COMPLETED,
        payload={
            "step": phase.kind.value,
            "event": "review.pending",
            "task_key": task_key,
            "task_id": str(opened.task_id),
            "items": len(items),
        },
        job_status=JobStatus.PROCESSING,
    )

    resolution = await ctx.wait_for_task(task_key)
    state.scratch.setdefault("resolutions", {})[phase.id] = resolution

    rejected = resolution.get("approved") is False
    comment = resolution.get("comment")
    event_payload = {"taskId": str(opened.task_id)}
    if comment:
        event_payload["comment"] = comment
    if rejected:
        await append_case_event(
            state,
            REVIEW_REJECTED_EVENT,
            event_payload,
            dedupe_key=f"{task_key}:{REVIEW_REJECTED_EVENT}",
        )
        await transition_case(state, WorkflowCaseStatus.REJECTED.value, reason=phase.id)
        state.terminated = True
        return
    await append_case_event(
        state,
        REVIEW_APPROVED_EVENT,
        event_payload,
        dedupe_key=f"{task_key}:{REVIEW_APPROVED_EVENT}",
    )
    await transition_case(state, WorkflowCaseStatus.PROCESSING.value, reason=f"{phase.id}.resolved")


# ─── human_review (E4 · aprobación configurable + review-gate) ───────────────


@register_phase(PhaseKind.HUMAN_REVIEW.value, scope="case")
async def human_review(ctx, phase, state: PipelineState) -> None:
    cfg = HumanReviewConfig.model_validate(phase.config or {})
    kind_cfg = cfg.kind
    if kind_cfg == "approval" and case_context(state) is not None:
        # E5 · §3.1: ActivationPolicy.stages presente ⇒ revisión multinivel.
        # Ausente ⇒ gate único E4 INTACTO (compat total).
        policy = _activation_policy(state)
        if policy.stages:
            await _staged_review(ctx, phase, state, policy)
            return
        await _approval_gate(ctx, phase, state)
        return
    if kind_cfg in ("approval", "review") and case_context(state) is None:
        # Run suelto: las semánticas de caso no aplican — skip limpio.
        workflow.logger.info(f"pipeline.human_review.skipped reason=no_case job_id={state.job_id}")
        return
    await _open_and_wait(
        ctx,
        phase,
        state,
        kind=HumanTaskKind.APPROVAL,
        default_assignee=HumanTaskAssigneeMode.INTERNAL_QUEUE,
        event_name="review.pending",
    )


def _votes_as_tally(votes: list[dict], *, distinct_approvers: bool) -> tuple[int, int]:
    """Cuenta (approvals, rejections) de las resoluciones acumuladas (cada una
    ``{approved, resolvedBy, ...}``) reusando ``tally_votes``."""
    shaped = {"votes": [{"approved": v.get("approved"), "actor": v.get("resolvedBy")} for v in votes]}
    return tally_votes(shaped, distinct_approvers=distinct_approvers)


async def _await_quorum(ctx, task_key: str, cfg, pool: int) -> tuple[bool, str | None]:
    """F4 · D-I: bloquea hasta que el quórum se decide (approved/rejected) o, si
    ``timeout`` está fijado, hasta expirar ⇒ **auto-rechazo** (fail-safe). Cada
    voto llega vía la señal ``task_resolved`` (acumulada en ``ctx._votes``)."""

    def _decided() -> bool:
        approvals, rejections = _votes_as_tally(
            ctx._votes.get(task_key, []), distinct_approvers=cfg.distinct_approvers
        )
        return evaluate_quorum(approvals, rejections, cfg.approvals_required, pool) != "pending"

    timeout_td = parse_duration(cfg.timeout, None)
    if timeout_td is not None:
        try:
            await workflow.wait_condition(_decided, timeout=timeout_td)
        except asyncio.TimeoutError:
            return False, None  # auto-reject (fail-safe)
    else:
        await workflow.wait_condition(_decided)

    votes = ctx._votes.get(task_key, [])
    approvals, rejections = _votes_as_tally(votes, distinct_approvers=cfg.distinct_approvers)
    decision = evaluate_quorum(approvals, rejections, cfg.approvals_required, pool)
    comment = votes[-1].get("comment") if votes else None
    return decision == "approved", comment


async def _approval_gate(ctx, phase, state: PipelineState) -> None:
    """Gate de aprobación post-analyze (ActivationPolicy.mode)."""
    tenant_id, workflow_id, case_id = case_context(state)
    cfg = HumanReviewConfig.model_validate(phase.config or {})
    policy = _activation_policy(state)

    activated = True
    activation_reason = "mandatory"
    if policy.mode == "by_exception":
        check: CheckBlockingResultsOutput = await workflow.execute_activity(
            CHECK_BLOCKING_RESULTS_ACTIVITY,
            CheckBlockingResultsInput(
                tenant_id=tenant_id,
                case_id=case_id,
                severities=policy.blocking_rule_severities,
            ),
            result_type=CheckBlockingResultsOutput,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
        sampled = deterministic_sample(state.job_id, policy.sample_rate)
        activated = check.blocking or sampled
        activation_reason = "blocking" if check.blocking else "sampling" if sampled else "none"

    if not activated:
        await append_case_event(
            state,
            REVIEW_SKIPPED_EVENT,
            {"mode": policy.mode},
            dedupe_key=f"{_task_key(phase)}:{REVIEW_SKIPPED_EVENT}",
        )
        state.put_artifact("approval", {"activated": False, "mode": policy.mode})
        return

    task_key = _task_key(phase)
    opened: OpenCaseTaskOutput = await workflow.execute_activity(
        OPEN_APPROVAL_TASK_ACTIVITY,
        OpenApprovalTaskInput(
            task_key=task_key,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            case_id=case_id,
            pipeline_run_id=workflow.info().workflow_id,
            trigger="approval",
            audience=cfg.audience,
            approvals_required=cfg.approvals_required,
            distinct_approvers=cfg.distinct_approvers,
            approver_users=cfg.approvers.users,
            approver_roles=cfg.approvers.roles,
            approver_audience=cfg.approvers.audience,
        ),
        result_type=OpenCaseTaskOutput,
        start_to_close_timeout=timedelta(seconds=30),
        retry_policy=DEFAULT_RETRY_POLICY,
    )

    await transition_case(state, WorkflowCaseStatus.NEEDS_REVIEW.value, reason=phase.id)
    webhook_payload = {
        "caseId": opened.payload.get("caseId") or str(case_id),
        "taskId": str(opened.task_id),
        "verdict": opened.payload.get("verdict"),
        "summary": opened.payload.get("summary"),
        "resolveUrl": opened.payload.get("resolveUrl") or f"/v1/tasks/{opened.task_id}/resolve",
    }
    await _dispatch_case_task_event(
        state,
        event_type=WebhookEventType.CASE_NEEDS_REVIEW.value,
        task_id=opened.task_id,
        payload=webhook_payload,
    )
    await ctx._checkpoint(
        state.data,
        type=ProcessingJobEventType.STEP_COMPLETED,
        payload={
            "step": phase.kind.value,
            "event": "review.pending",
            "task_key": task_key,
            "task_id": str(opened.task_id),
            "reason": activation_reason,
        },
        job_status=JobStatus.PROCESSING,
    )

    # F4 · D-I: quórum N-de-M. Default (N=1) == el gate single de hoy
    # (byte-idéntico). N>1 acumula votos vía la señal ``task_resolved`` hasta
    # alcanzar/volver inalcanzable el quórum, o auto-rechaza al expirar ``timeout``.
    pool = quorum_pool_size(len(cfg.approvers.users), cfg.approvals_required)
    if cfg.approvals_required <= 1:
        resolution = await ctx.wait_for_task(task_key)
        state.scratch.setdefault("resolutions", {})[phase.id] = resolution
        approvals, rejections = tally_votes(resolution, distinct_approvers=cfg.distinct_approvers)
        decision = evaluate_quorum(approvals, rejections, cfg.approvals_required, pool)
        approved = decision == "approved" if decision != "pending" else bool(resolution.get("approved"))
        comment = resolution.get("comment")
    else:
        approved, comment = await _await_quorum(ctx, task_key, cfg, pool)
        state.scratch.setdefault("resolutions", {})[phase.id] = {"votes": ctx._votes.get(task_key, [])}
    event_payload = {"taskId": str(opened.task_id)}
    if comment:
        event_payload["comment"] = comment
    if approved:
        await append_case_event(
            state,
            REVIEW_APPROVED_EVENT,
            event_payload,
            dedupe_key=f"{task_key}:{REVIEW_APPROVED_EVENT}",
        )
        state.put_artifact(
            "approval",
            {"activated": True, "approved": True, "approvals_required": cfg.approvals_required},
        )
        return
    await append_case_event(
        state,
        REVIEW_REJECTED_EVENT,
        event_payload,
        dedupe_key=f"{task_key}:{REVIEW_REJECTED_EVENT}",
    )
    await transition_case(state, WorkflowCaseStatus.REJECTED.value, reason=phase.id)
    state.put_artifact("approval", {"activated": True, "approved": False})
    # Rechazo: NO output, NO deliver — el run termina OK (no FAILED).
    state.terminated = True


# ─── human_review multinivel (E5 · diseño §3.1/§3.3) ─────────────────────────


async def _stage_gate_items(state: PipelineState, stage: str) -> list[dict]:
    """Gate items frescos del stage — relee los docs del caso vía activity
    (jamás payload de señal); el L2 viene filtrado por verification (Rossum)."""
    tenant_id, _workflow_id, case_id = case_context(state)
    raw_policy = (state.scratch.get("policies") or {}).get("activation") or {}
    result: BuildStageGateItemsOutput = await workflow.execute_activity(
        BUILD_STAGE_GATE_ITEMS_ACTIVITY,
        BuildStageGateItemsInput(
            tenant_id=tenant_id,
            case_id=case_id,
            activation_policy=raw_policy,
            exclude_verified_level=STAGE_EXCLUDE_VERIFIED_LEVEL.get(stage),
        ),
        result_type=BuildStageGateItemsOutput,
        start_to_close_timeout=timedelta(seconds=60),
        retry_policy=DEFAULT_RETRY_POLICY,
    )
    return result.items


async def _check_blocking(state: PipelineState, policy: ActivationPolicy) -> bool:
    tenant_id, _workflow_id, case_id = case_context(state)
    check: CheckBlockingResultsOutput = await workflow.execute_activity(
        CHECK_BLOCKING_RESULTS_ACTIVITY,
        CheckBlockingResultsInput(
            tenant_id=tenant_id,
            case_id=case_id,
            severities=policy.blocking_rule_severities,
        ),
        result_type=CheckBlockingResultsOutput,
        start_to_close_timeout=timedelta(seconds=30),
        retry_policy=DEFAULT_RETRY_POLICY,
    )
    return check.blocking


async def _run_reanalysis(state: PipelineState) -> str | None:
    """Re-analyze tras corrections (§3.3): child workflow con run NUEVO,
    reproduciendo la MISMA config sellada por la fase analyze (phases-config
    H1/H2: overrides de provider + ``rule_set``). Best-effort: un re-analyze
    fallido NO tumba el run pausado en revisión."""
    tenant_id, workflow_id, case_id = case_context(state)
    run_id = workflow.uuid4()
    # H1/H2: recupera la config sellada del artifact analyze. Ausente (runs en
    # vuelo previos al fix / sin caso) ⇒ defaults = env providers + todas las
    # reglas (idéntico al comportamiento anterior, replay-safe).
    run_cfg = state.artifact("analysis_run") or {}
    providers = AnalysisProviders(**(run_cfg.get("providers") or {}))
    rule_set = run_cfg.get("rule_set")
    try:
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
            schedule_to_close_timeout=ACTIVE_RUN_WAIT_TIMEOUT,
            retry_policy=_CREATE_RUN_RETRY,
        )
        await workflow.execute_child_workflow(
            ANALYSIS_CHILD_WORKFLOW,
            AnalysisRunWorkflowInput(
                run_id=run_id,
                workflow_id=workflow_id,
                case_id=case_id,
                tenant_id=tenant_id,
                providers=providers,
                rule_set=rule_set,
            ),
            id=workflow_id_for_run(run_id),
            parent_close_policy=ParentClosePolicy.ABANDON,
        )
        return str(run_id)
    except Exception:  # noqa: BLE001 — el stage sigue esperando resolución
        workflow.logger.warning(f"pipeline.review_reanalysis_failed case_id={case_id} run_id={run_id}")
        try:
            await workflow.execute_activity(
                MARK_ANALYSIS_RUN_FAILED_ACTIVITY,
                MarkAnalysisRunFailedInput(run_id=run_id, tenant_id=tenant_id, error="review re-analysis failed"),
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=DEFAULT_RETRY_POLICY,
            )
        except Exception:  # noqa: BLE001
            pass
        return None


async def _staged_review(ctx, phase, state: PipelineState, policy: ActivationPolicy) -> None:
    """Loop de stages L1/L2 (§3.1) con corrections→re-analyze (§3.3).

    Por stage: activación (mandatory | by_exception: blocking ∨ sampling ∨
    gate items abiertos) → REVIEW_L1/REVIEW_L2 + HumanTask con ``stage`` y
    task_key ``{run}:{phase}:{stage}`` → espera resolución O corrections
    (las corrections re-analizan y se SIGUE esperando; un approved con
    re-analyze en vuelo se aplica después). Rechazo en cualquier stage ⇒
    REJECTED + terminated. Todos aprobados/skipped ⇒ webhook
    ``case.review.completed`` + transición a PROCESSING (si algún stage activó).
    """
    tenant_id, workflow_id, case_id = case_context(state)
    run_id = workflow.info().workflow_id
    stage_outcomes: list[dict] = []
    corrections_total = 0
    last_task_id = None
    activated_any = False

    for review_stage in policy.stages or []:
        stage = review_stage.stage
        task_key = f"{run_id}:{phase.id}:{stage}"
        items = await _stage_gate_items(state, stage)

        activated = True
        activation_reason = "mandatory"
        if review_stage.mode == "by_exception":
            blocking = await _check_blocking(state, policy)
            # Sampling determinista por job+stage (sha256 — jamás random).
            sampled = deterministic_sample(f"{state.job_id}:{stage}", policy.sample_rate)
            activated = blocking or sampled or bool(items)
            activation_reason = (
                "blocking" if blocking else "sampling" if sampled else "gate_items" if items else "none"
            )

        if not activated:
            await append_case_event(
                state,
                REVIEW_SKIPPED_EVENT,
                {"mode": review_stage.mode, "stage": stage},
                dedupe_key=f"{task_key}:{REVIEW_SKIPPED_EVENT}",
            )
            stage_outcomes.append({"stage": stage, "outcome": "skipped"})
            continue

        activated_any = True
        opened: OpenCaseTaskOutput = await workflow.execute_activity(
            OPEN_APPROVAL_TASK_ACTIVITY,
            OpenApprovalTaskInput(
                task_key=task_key,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                case_id=case_id,
                pipeline_run_id=run_id,
                trigger="approval",
                gate_items=items,
                audience=STAGE_AUDIENCE.get(stage),
                stage=stage,
            ),
            result_type=OpenCaseTaskOutput,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
        last_task_id = opened.task_id

        await transition_case(state, REVIEW_STAGE_STATUS[stage], reason=f"{phase.id}:{stage}")
        webhook_payload = {
            "caseId": opened.payload.get("caseId") or str(case_id),
            "taskId": str(opened.task_id),
            "stage": stage,
            "verdict": opened.payload.get("verdict"),
            "summary": opened.payload.get("summary"),
            "items": opened.payload.get("items") or [],
            "resolveUrl": opened.payload.get("resolveUrl") or f"/v1/tasks/{opened.task_id}/resolve",
        }
        await _dispatch_case_task_event(
            state,
            event_type=WebhookEventType.CASE_NEEDS_REVIEW.value,
            task_id=opened.task_id,
            payload=webhook_payload,
        )
        await ctx._checkpoint(
            state.data,
            type=ProcessingJobEventType.STEP_COMPLETED,
            payload={
                "step": phase.kind.value,
                "event": "review.pending",
                "stage": stage,
                "task_key": task_key,
                "task_id": str(opened.task_id),
                "reason": activation_reason,
            },
            job_status=JobStatus.PROCESSING,
        )

        # Espera del stage: resolución O corrections (§3.3). Las corrections
        # re-analizan (run nuevo) y refrescan blocking/gate items; un approved
        # recibido con re-analyze pendiente se aplica DESPUÉS (invariante).
        while True:
            signal_kind, signal_payload = await ctx.wait_for_task_or_corrections(task_key)
            if signal_kind == "resolved":
                resolution = signal_payload
                break
            fields = (signal_payload or {}).get("fields") or []
            corrections_total += len(fields)
            rerun_id = await _run_reanalysis(state)
            blocking_after = await _check_blocking(state, policy)
            items = await _stage_gate_items(state, stage)
            if rerun_id is not None:
                await append_case_event(
                    state,
                    ANALYSIS_RERUN_EVENT,
                    {
                        "runId": rerun_id,
                        "stage": stage,
                        "fields": len(fields),
                        "blocking": blocking_after,
                        "openItems": len(items),
                    },
                    dedupe_key=f"{task_key}:{ANALYSIS_RERUN_EVENT}:{rerun_id}",
                )

        state.scratch.setdefault("resolutions", {})[f"{phase.id}:{stage}"] = resolution
        approved = bool(resolution.get("approved"))
        comment = resolution.get("comment")
        actor = resolution.get("resolvedBy")
        event_payload = {"taskId": str(opened.task_id), "stage": stage}
        if comment:
            event_payload["comment"] = comment
        if actor:
            event_payload["actor"] = actor

        if not approved:
            await append_case_event(
                state,
                REVIEW_REJECTED_EVENT,
                event_payload,
                dedupe_key=f"{task_key}:{REVIEW_REJECTED_EVENT}",
            )
            await transition_case(state, WorkflowCaseStatus.REJECTED.value, reason=f"{phase.id}:{stage}")
            stage_outcomes.append(
                {"stage": stage, "outcome": "rejected", "actor": actor, "taskId": str(opened.task_id)}
            )
            state.put_artifact(
                "approval",
                {"activated": True, "approved": False, "stage": stage, "stages": stage_outcomes},
            )
            # Rechazo en CUALQUIER stage: NO output, NO deliver — run termina OK.
            state.terminated = True
            return

        await append_case_event(
            state,
            REVIEW_APPROVED_EVENT,
            event_payload,
            dedupe_key=f"{task_key}:{REVIEW_APPROVED_EVENT}",
        )
        stage_outcomes.append({"stage": stage, "outcome": "approved", "actor": actor, "taskId": str(opened.task_id)})

    # Todos los stages aprobados/skipped ⇒ webhook nuevo + reanudar el tail.
    await _dispatch_case_task_event(
        state,
        event_type=WebhookEventType.CASE_REVIEW_COMPLETED.value,
        task_id=last_task_id,
        payload={
            "caseId": str(case_id),
            "stages": stage_outcomes,
            "corrections": corrections_total,
        },
    )
    if activated_any:
        await transition_case(state, WorkflowCaseStatus.PROCESSING.value, reason=f"{phase.id}.review_completed")
    state.put_artifact(
        "approval",
        {
            "activated": activated_any,
            "approved": True,
            "stages": stage_outcomes,
            "corrections": corrections_total,
        },
    )


