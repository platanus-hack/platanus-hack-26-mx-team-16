"""E4 · diseño §4: await_documents / await_clarification / human_review.

Mismo harness que el resto de la suite de fases: ``temporalio.workflow``
monkeypatcheado y handler invocado directo con un ``ProcessingJobWorkflowBase``
real (contadores de señales + wait_for_task incluidos).
"""

from __future__ import annotations

import asyncio
import hashlib
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from expects import be_false, be_none, be_true, contain, equal, expect, have_length
from temporalio import workflow as tw

from src.common.domain.entities.workflows.analysis_run_processing import (
    CreateAnalysisRunForPipelineOutput,
)
from src.common.domain.entities.workflows.case_runtime import (
    CheckBlockingResultsOutput,
    EvaluateActivationGateOutput,
    EvaluateCaseCompletenessOutput,
    MarkCaseReadyOutput,
    OpenCaseTaskOutput,
)
from src.common.domain.entities.workflows.document_processing import DocumentProcessingInput
from src.common.domain.entities.workflows.human_task_io import CreateHumanTaskOutput
from src.common.domain.enums.pipelines import PhaseKind
from src.common.domain.enums.webhooks import WebhookEventType
from src.workflows.application.pipelines import pause_phases as pp
from src.workflows.application.pipelines.case_transitions import (
    APPEND_CASE_EVENT_ACTIVITY,
    TRANSITION_CASE_STATUS_ACTIVITY,
)
from src.workflows.application.pipelines.pause_phases import (
    CHECK_BLOCKING_RESULTS_ACTIVITY,
    CREATE_HUMAN_TASK_ACTIVITY,
    DISPATCH_CASE_EVENT_ACTIVITY,
    EVALUATE_CASE_COMPLETENESS_ACTIVITY,
    MARK_CASE_READY_ACTIVITY,
    OPEN_APPROVAL_TASK_ACTIVITY,
    OPEN_CLARIFICATION_TASK_ACTIVITY,
    deterministic_sample,
)
from src.workflows.application.pipelines.runtime import PipelineState
from src.workflows.domain.models.pipeline import PhaseSpec
from src.workflows.presentation.workflows.base import ProcessingJobWorkflowBase

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")
_CASE = UUID("44444444-4444-4444-4444-444444444444")
_TASK_ID = UUID("55555555-5555-5555-5555-555555555555")


def _state(*, policies: dict | None = None) -> PipelineState:
    data = DocumentProcessingInput(
        object_key="",
        document_types=[],
        job_id="CASE#abc",
        case_id=_CASE,
        workflow_id=_WORKFLOW,
        tenant_id=_TENANT,
        persist=True,
    )
    state = PipelineState(data=data, job_id="CASE#abc")
    state.scratch["policies"] = policies or {"activation": None, "completeness": None}
    return state


def _patch(monkeypatch, calls: list, responses: dict, *, on_wait=None) -> None:
    async def fake_execute_activity(name, arg=None, **kwargs):
        calls.append((name, arg))
        canned = responses.get(name)
        if callable(canned):
            return canned(arg)
        return canned

    async def fake_wait_condition(predicate, *a, **k):
        if on_wait is not None:
            on_wait()

    monkeypatch.setattr(tw, "execute_activity", fake_execute_activity)
    monkeypatch.setattr(tw, "wait_condition", fake_wait_condition)
    monkeypatch.setattr(tw, "info", lambda: SimpleNamespace(workflow_id="run-1", run_id="r1"))
    monkeypatch.setattr(tw, "logger", SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None))


def _transitions(calls: list) -> list[str]:
    return [arg.to_status for name, arg in calls if name == TRANSITION_CASE_STATUS_ACTIVITY]


def _events(calls: list) -> list[str]:
    return [arg.type for name, arg in calls if name == APPEND_CASE_EVENT_ACTIVITY]


def _completeness(satisfied: bool, auto_ready: bool = False) -> EvaluateCaseCompletenessOutput:
    return EvaluateCaseCompletenessOutput(
        satisfied=satisfied,
        auto_ready=auto_ready,
        required={"anexo": 1},
        present={"anexo": 1 if satisfied else 0},
        missing=[] if satisfied else [{"documentType": "anexo", "missing": 1}],
    )


# ─── await_documents ─────────────────────────────────────────────────────────


async def test_await_documents__auto_ready_proceeds_without_signals(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {
            EVALUATE_CASE_COMPLETENESS_ACTIVITY: _completeness(True),
            MARK_CASE_READY_ACTIVITY: MarkCaseReadyOutput(ready_at="2026-06-10T00:00:00+00:00", transitioned=True),
        },
    )
    state = _state(policies={"activation": None, "completeness": {"required_types": {"anexo": 1}, "auto_ready": True}})
    ctx = ProcessingJobWorkflowBase()

    await pp.await_documents(ctx, PhaseSpec(id="await", kind=PhaseKind.AWAIT_DOCUMENTS), state)

    evaluates = [arg for name, arg in calls if name == EVALUATE_CASE_COMPLETENESS_ACTIVITY]
    marks = [arg for name, arg in calls if name == MARK_CASE_READY_ACTIVITY]
    expect(evaluates).to(have_length(1))
    expect(marks).to(have_length(1))
    expect(marks[0].auto).to(be_true)
    expect(marks[0].forced).to(be_false)
    expect(state.artifact("await_documents")["satisfied"]).to(be_true)


async def test_await_documents__ready_force_proceeds_even_unsatisfied(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {
            EVALUATE_CASE_COMPLETENESS_ACTIVITY: _completeness(False),
            MARK_CASE_READY_ACTIVITY: MarkCaseReadyOutput(ready_at="2026-06-10T00:00:00+00:00"),
        },
    )
    state = _state(policies={"activation": None, "completeness": {"required_types": {"anexo": 1}}})
    ctx = ProcessingJobWorkflowBase()
    ctx._case_ready_requested = True
    ctx._case_ready_force = True  # POST /ready {force: true} ya llegó

    await pp.await_documents(ctx, PhaseSpec(id="await", kind=PhaseKind.AWAIT_DOCUMENTS), state)

    marks = [arg for name, arg in calls if name == MARK_CASE_READY_ACTIVITY]
    expect(marks).to(have_length(1))
    expect(marks[0].forced).to(be_true)
    expect(state.artifact("await_documents")["forced"]).to(be_true)


async def test_await_documents__waits_for_signal_then_reevaluates(monkeypatch):
    calls: list = []
    evaluations = iter([_completeness(False), _completeness(True)])
    ctx = ProcessingJobWorkflowBase()

    def on_wait():
        # Señal case_ready llegando mientras esperábamos (sin force).
        ctx._case_ready_count += 1
        ctx._case_ready_requested = True

    _patch(
        monkeypatch,
        calls,
        {
            EVALUATE_CASE_COMPLETENESS_ACTIVITY: lambda arg: next(evaluations),
            MARK_CASE_READY_ACTIVITY: MarkCaseReadyOutput(ready_at="2026-06-10T00:00:00+00:00"),
        },
        on_wait=on_wait,
    )
    state = _state(policies={"activation": None, "completeness": {"required_types": {"anexo": 1}}})

    await pp.await_documents(ctx, PhaseSpec(id="await", kind=PhaseKind.AWAIT_DOCUMENTS), state)

    evaluates = [arg for name, arg in calls if name == EVALUATE_CASE_COMPLETENESS_ACTIVITY]
    expect(evaluates).to(have_length(2))  # insatisfecho → señal → re-evaluación
    marks = [arg for name, arg in calls if name == MARK_CASE_READY_ACTIVITY]
    expect(marks).to(have_length(1))
    expect(marks[0].forced).to(be_false)


async def test_await_documents__satisfied_without_auto_ready_waits_for_explicit_ready(monkeypatch):
    # Sin policy/required vacío ⇒ satisfied=True, pero espera el ready explícito.
    calls: list = []
    ctx = ProcessingJobWorkflowBase()

    def on_wait():
        ctx._case_ready_count += 1
        ctx._case_ready_requested = True

    _patch(
        monkeypatch,
        calls,
        {
            EVALUATE_CASE_COMPLETENESS_ACTIVITY: _completeness(True),
            MARK_CASE_READY_ACTIVITY: MarkCaseReadyOutput(ready_at="2026-06-10T00:00:00+00:00"),
        },
        on_wait=on_wait,
    )
    state = _state()  # completeness policy None

    await pp.await_documents(ctx, PhaseSpec(id="await", kind=PhaseKind.AWAIT_DOCUMENTS), state)

    evaluates = [arg for name, arg in calls if name == EVALUATE_CASE_COMPLETENESS_ACTIVITY]
    expect(evaluates).to(have_length(2))  # primera pasada NO procede (sin ready)


async def test_await_documents__skips_clean_without_case(monkeypatch):
    calls: list = []
    _patch(monkeypatch, calls, {})
    data = DocumentProcessingInput(object_key="s3://b/x", document_types=[], job_id="J", tenant_id=_TENANT)
    state = PipelineState(data=data, job_id="J")

    await pp.await_documents(ProcessingJobWorkflowBase(), PhaseSpec(id="await", kind=PhaseKind.AWAIT_DOCUMENTS), state)

    expect(calls).to(equal([]))


# ─── await_clarification ─────────────────────────────────────────────────────


def _gate_item() -> dict:
    return {
        "documentId": str(uuid4()),
        "documentType": "factura",
        "fieldPath": "total",
        "confidence": 0.3,
        "threshold": 0.75,
        "parseConfidence": 0.3,
        "extractConfidence": None,
        "signals": ["ocr_blur"],
        "candidates": ["100"],
        "page": 1,
        "bbox": None,
    }


def _activation(on_low_confidence: str) -> dict:
    return {"activation": {"on_low_confidence": on_low_confidence}, "completeness": None}


async def test_extraction_gate__clarify_opens_task_and_transitions(monkeypatch):
    # Breach + on_low_confidence=clarify ⇒ tarea de aclaración al remitente.
    calls: list = []
    request = {
        "caseId": str(_CASE),
        "taskId": str(_TASK_ID),
        "items": [],
        "resolveUrl": f"/v1/tasks/{_TASK_ID}/resolve",
        "expiresAt": None,
    }
    _patch(
        monkeypatch,
        calls,
        {
            pp.EVALUATE_ACTIVATION_GATE_ACTIVITY: EvaluateActivationGateOutput(items=[_gate_item()]),
            OPEN_CLARIFICATION_TASK_ACTIVITY: OpenCaseTaskOutput(task_id=_TASK_ID, payload=request),
        },
    )
    state = _state(policies=_activation("clarify"))
    ctx = ProcessingJobWorkflowBase()
    ctx._resolved_tasks["run-1:gate"] = {"total": "700"}

    await pp.extraction_gate(ctx, PhaseSpec(id="gate", kind=PhaseKind.EXTRACTION_GATE), state)

    opened = [arg for name, arg in calls if name == OPEN_CLARIFICATION_TASK_ACTIVITY]
    expect(opened).to(have_length(1))
    expect(opened[0].task_key).to(equal("run-1:gate"))
    expect(opened[0].items).to(have_length(1))

    dispatches = [arg for name, arg in calls if name == DISPATCH_CASE_EVENT_ACTIVITY]
    expect(dispatches).to(have_length(1))
    expect(dispatches[0].event_type).to(equal(WebhookEventType.CASE_NEEDS_CLARIFICATION.value))

    expect(_transitions(calls)).to(equal(["NEEDS_CLARIFICATION", "PROCESSING"]))
    expect(_events(calls)).to(equal(["clarification.resolved"]))
    expect(state.scratch["resolutions"]["gate"]).to(equal({"total": "700"}))


async def test_extraction_gate__no_breaches_continue(monkeypatch):
    calls: list = []
    _patch(monkeypatch, calls, {pp.EVALUATE_ACTIVATION_GATE_ACTIVITY: EvaluateActivationGateOutput(items=[])})
    state = _state(policies=_activation("clarify"))

    await pp.extraction_gate(
        ProcessingJobWorkflowBase(), PhaseSpec(id="gate", kind=PhaseKind.EXTRACTION_GATE), state
    )

    expect([n for n, _ in calls if n == OPEN_CLARIFICATION_TASK_ACTIVITY]).to(equal([]))
    expect(_transitions(calls)).to(equal([]))


async def test_extraction_gate__no_policy_is_noop(monkeypatch):
    calls: list = []
    _patch(monkeypatch, calls, {})
    state = _state(policies={"activation": None, "completeness": None})

    await pp.extraction_gate(
        ProcessingJobWorkflowBase(), PhaseSpec(id="gate", kind=PhaseKind.EXTRACTION_GATE), state
    )

    expect([n for n, _ in calls if n == pp.EVALUATE_ACTIVATION_GATE_ACTIVITY]).to(equal([]))


async def test_extraction_gate__skips_without_case(monkeypatch):
    # Run suelto (sin caso) ⇒ no-op limpio: ni evalúa la policy ni abre tarea.
    calls: list = []
    _patch(monkeypatch, calls, {})
    data = DocumentProcessingInput(
        object_key="s3://b/in.pdf",
        document_types=[],
        job_id="JOB-1",
        workflow_id=_WORKFLOW,
        tenant_id=_TENANT,
        persist=True,
    )
    state = PipelineState(data=data, job_id="JOB-1")
    state.scratch["policies"] = _activation("clarify")

    await pp.extraction_gate(
        ProcessingJobWorkflowBase(), PhaseSpec(id="gate", kind=PhaseKind.EXTRACTION_GATE), state
    )

    expect(calls).to(equal([]))


# El branch on_timeout se testea sobre _on_clarification_timeout directo (la
# espera con timeout es glue fino; el valor está en escalate/fail/auto_resolve).


async def test_clarification_timeout__escalate_emits_event_and_unblocks(monkeypatch):
    from src.workflows.domain.models.phase_configs import AwaitClarificationConfig

    calls: list = []
    _patch(monkeypatch, calls, {})
    state = _state()
    cfg = AwaitClarificationConfig(on_timeout="escalate")

    result = await pp._on_clarification_timeout(
        ProcessingJobWorkflowBase(),
        PhaseSpec(id="clar1", kind=PhaseKind.AWAIT_CLARIFICATION),
        state,
        "run-1:clar1",
        cfg,
        SimpleNamespace(task_id=_TASK_ID),
    )

    expect(result).to(equal({"escalated": True}))
    expect(_events(calls)).to(equal(["clarification.escalated"]))


async def test_clarification_timeout__fail_marks_case_failed_and_raises(monkeypatch):
    from temporalio.exceptions import ApplicationError

    from src.workflows.domain.models.phase_configs import AwaitClarificationConfig

    calls: list = []
    _patch(monkeypatch, calls, {})
    state = _state()
    cfg = AwaitClarificationConfig(on_timeout="fail")

    with pytest.raises(ApplicationError):
        await pp._on_clarification_timeout(
            ProcessingJobWorkflowBase(),
            PhaseSpec(id="clar1", kind=PhaseKind.AWAIT_CLARIFICATION),
            state,
            "run-1:clar1",
            cfg,
            SimpleNamespace(task_id=_TASK_ID),
        )

    expect(_transitions(calls)).to(contain("FAILED"))


async def test_await_clarification__opens_f6_task_without_transitions(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {CREATE_HUMAN_TASK_ACTIVITY: lambda arg: CreateHumanTaskOutput(task_id=_TASK_ID, task_key=arg.task_key)},
    )
    state = _state()  # F6 standalone: pausa de aclaración incondicional (sin gate)
    ctx = ProcessingJobWorkflowBase()
    ctx._resolved_tasks["run-1:clar1"] = {"ok": True}

    await pp.await_clarification(ctx, PhaseSpec(id="clar1", kind=PhaseKind.AWAIT_CLARIFICATION), state)

    created = [arg for name, arg in calls if name == CREATE_HUMAN_TASK_ACTIVITY]
    expect(created).to(have_length(1))
    expect(_transitions(calls)).to(equal([]))  # flujo F6 puro: sin transiciones


# ─── human_review · approval ─────────────────────────────────────────────────


def _approval_payload() -> dict:
    return {
        "caseId": str(_CASE),
        "taskId": str(_TASK_ID),
        "verdict": "REVIEW",
        "summary": {"confidenceScore": 0.8},
        "signals": [],
        "resolveUrl": f"/v1/tasks/{_TASK_ID}/resolve",
    }


async def test_approval__mandatory_pauses_and_approve_continues(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {OPEN_APPROVAL_TASK_ACTIVITY: OpenCaseTaskOutput(task_id=_TASK_ID, payload=_approval_payload())},
    )
    state = _state(policies={"activation": {"mode": "mandatory"}, "completeness": None})
    ctx = ProcessingJobWorkflowBase()
    ctx._resolved_tasks["run-1:approval"] = {"approved": True, "comment": "todo bien"}

    await pp.human_review(
        ctx, PhaseSpec(id="approval", kind=PhaseKind.HUMAN_REVIEW, config={"kind": "approval"}), state
    )

    expect(_transitions(calls)).to(equal(["NEEDS_REVIEW"]))
    dispatches = [arg for name, arg in calls if name == DISPATCH_CASE_EVENT_ACTIVITY]
    expect(dispatches).to(have_length(1))
    expect(dispatches[0].event_type).to(equal(WebhookEventType.CASE_NEEDS_REVIEW.value))
    expect(dispatches[0].payload["verdict"]).to(equal("REVIEW"))
    expect(dispatches[0].payload["resolveUrl"]).to(equal(f"/v1/tasks/{_TASK_ID}/resolve"))
    expect(_events(calls)).to(equal(["review.approved"]))
    expect(state.terminated).to(be_false)


async def test_approval__reject_appends_event_transitions_rejected_and_terminates(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {OPEN_APPROVAL_TASK_ACTIVITY: OpenCaseTaskOutput(task_id=_TASK_ID, payload=_approval_payload())},
    )
    state = _state(policies={"activation": {"mode": "mandatory"}, "completeness": None})
    ctx = ProcessingJobWorkflowBase()
    ctx._resolved_tasks["run-1:approval"] = {"approved": False, "comment": "monto no cuadra"}

    await pp.human_review(
        ctx, PhaseSpec(id="approval", kind=PhaseKind.HUMAN_REVIEW, config={"kind": "approval"}), state
    )

    expect(_transitions(calls)).to(equal(["NEEDS_REVIEW", "REJECTED"]))
    events = [arg for name, arg in calls if name == APPEND_CASE_EVENT_ACTIVITY]
    expect([e.type for e in events]).to(equal(["review.rejected"]))
    expect(events[0].payload["comment"]).to(equal("monto no cuadra"))
    expect(state.terminated).to(be_true)  # NO output, NO deliver — run termina OK


def _quorum_config(**over) -> dict:
    base = {"kind": "approval", "approvals_required": 2, "approvers": {"users": ["u1", "u2", "u3"]}}
    return {**base, **over}


async def test_approval_quorum__two_of_three_approvals_passes(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {OPEN_APPROVAL_TASK_ACTIVITY: OpenCaseTaskOutput(task_id=_TASK_ID, payload=_approval_payload())},
    )
    state = _state(policies={"activation": {"mode": "mandatory"}, "completeness": None})
    ctx = ProcessingJobWorkflowBase()
    ctx._votes["run-1:approval"] = [
        {"approved": True, "resolvedBy": "u1"},
        {"approved": True, "resolvedBy": "u2"},
    ]

    await pp.human_review(ctx, PhaseSpec(id="approval", kind=PhaseKind.HUMAN_REVIEW, config=_quorum_config()), state)

    expect(_events(calls)).to(equal(["review.approved"]))
    expect(state.terminated).to(be_false)


async def test_approval_quorum__rejections_make_unreachable_rejects(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {OPEN_APPROVAL_TASK_ACTIVITY: OpenCaseTaskOutput(task_id=_TASK_ID, payload=_approval_payload())},
    )
    state = _state(policies={"activation": {"mode": "mandatory"}, "completeness": None})
    ctx = ProcessingJobWorkflowBase()
    # pool=3, N=2: dos rechazos ⇒ solo 1 elegible queda ⇒ inalcanzable ⇒ rejected.
    ctx._votes["run-1:approval"] = [
        {"approved": False, "resolvedBy": "u1"},
        {"approved": False, "resolvedBy": "u2"},
    ]

    await pp.human_review(ctx, PhaseSpec(id="approval", kind=PhaseKind.HUMAN_REVIEW, config=_quorum_config()), state)

    expect(_transitions(calls)).to(equal(["NEEDS_REVIEW", "REJECTED"]))
    expect(_events(calls)).to(equal(["review.rejected"]))
    expect(state.terminated).to(be_true)


async def test_await_quorum__timeout_auto_rejects(monkeypatch):
    # El branch de timeout se testea sobre _await_quorum directo (una sola
    # wait_condition) para no chocar con otros waits del flujo.
    from src.workflows.domain.models.phase_configs import ApproverSpec, HumanReviewConfig

    async def _raise_timeout(predicate, *a, **k):
        raise asyncio.TimeoutError

    monkeypatch.setattr(tw, "wait_condition", _raise_timeout)
    cfg = HumanReviewConfig(
        kind="approval", approvals_required=2, timeout="PT1S", approvers=ApproverSpec(users=["u1", "u2", "u3"])
    )
    ctx = ProcessingJobWorkflowBase()

    approved, comment = await pp._await_quorum(ctx, "run-1:approval", cfg, 3)

    expect(approved).to(be_false)  # fail-safe D-I: timeout ⇒ auto-reject
    expect(comment).to(be_none)


async def test_approval__by_exception_without_blocking_or_sampling_skips(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {CHECK_BLOCKING_RESULTS_ACTIVITY: CheckBlockingResultsOutput(blocking=False)},
    )
    state = _state(policies={"activation": {"mode": "by_exception", "sample_rate": 0}, "completeness": None})
    ctx = ProcessingJobWorkflowBase()

    await pp.human_review(
        ctx, PhaseSpec(id="approval", kind=PhaseKind.HUMAN_REVIEW, config={"kind": "approval"}), state
    )

    expect(_events(calls)).to(equal(["review.skipped"]))
    opened = [arg for name, arg in calls if name == OPEN_APPROVAL_TASK_ACTIVITY]
    expect(opened).to(equal([]))
    expect(_transitions(calls)).to(equal([]))
    expect(state.artifact("approval")).to(equal({"activated": False, "mode": "by_exception"}))


async def test_approval__by_exception_with_blocking_results_activates(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {
            CHECK_BLOCKING_RESULTS_ACTIVITY: CheckBlockingResultsOutput(blocking=True),
            OPEN_APPROVAL_TASK_ACTIVITY: OpenCaseTaskOutput(task_id=_TASK_ID, payload=_approval_payload()),
        },
    )
    state = _state(policies={"activation": {"mode": "by_exception", "sample_rate": 0}, "completeness": None})
    ctx = ProcessingJobWorkflowBase()
    ctx._resolved_tasks["run-1:approval"] = {"approved": True}

    await pp.human_review(
        ctx, PhaseSpec(id="approval", kind=PhaseKind.HUMAN_REVIEW, config={"kind": "approval"}), state
    )

    checks = [arg for name, arg in calls if name == CHECK_BLOCKING_RESULTS_ACTIVITY]
    expect(checks).to(have_length(1))
    expect(checks[0].severities).to(equal(["BLOCKER"]))
    expect(_transitions(calls)).to(equal(["NEEDS_REVIEW"]))


def test_deterministic_sample__sha256_bucket_is_stable_and_matches_threshold():
    bucket = (int(hashlib.sha256(b"JOB-X").hexdigest()[:8], 16) % 10**6) / 10**6

    expect(deterministic_sample("JOB-X", bucket + 0.000001)).to(be_true)
    expect(deterministic_sample("JOB-X", bucket)).to(be_false)  # estricto <
    expect(deterministic_sample("JOB-X", 0.0)).to(be_false)
    # Determinismo: misma entrada ⇒ mismo resultado (replay-safe).
    expect(deterministic_sample("JOB-X", 0.5)).to(equal(deterministic_sample("JOB-X", 0.5)))


# ─── extraction_gate · rama review ───────────────────────────────────────────


async def test_extraction_gate__review_opens_approval_and_resumes(monkeypatch):
    # Breach + on_low_confidence=review ⇒ tarea APPROVAL (trigger gate_review).
    calls: list = []
    payload = {"caseId": str(_CASE), "taskId": str(_TASK_ID), "items": [_gate_item()]}
    _patch(
        monkeypatch,
        calls,
        {
            pp.EVALUATE_ACTIVATION_GATE_ACTIVITY: EvaluateActivationGateOutput(items=[_gate_item()]),
            OPEN_APPROVAL_TASK_ACTIVITY: OpenCaseTaskOutput(task_id=_TASK_ID, payload=payload),
        },
    )
    state = _state(policies=_activation("review"))
    ctx = ProcessingJobWorkflowBase()
    ctx._resolved_tasks["run-1:gate"] = {"approved": True}

    await pp.extraction_gate(ctx, PhaseSpec(id="gate", kind=PhaseKind.EXTRACTION_GATE), state)

    opened = [arg for name, arg in calls if name == OPEN_APPROVAL_TASK_ACTIVITY]
    expect(opened).to(have_length(1))
    expect(opened[0].trigger).to(equal("gate_review"))
    expect(opened[0].gate_items).to(have_length(1))
    expect(_transitions(calls)).to(equal(["NEEDS_REVIEW", "PROCESSING"]))


async def test_human_review__legacy_config_keeps_f6_flow(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {CREATE_HUMAN_TASK_ACTIVITY: lambda arg: CreateHumanTaskOutput(task_id=_TASK_ID, task_key=arg.task_key)},
    )
    state = _state()
    ctx = ProcessingJobWorkflowBase()
    ctx._resolved_tasks["run-1:rev"] = {"approved": True}

    await pp.human_review(ctx, PhaseSpec(id="rev", kind=PhaseKind.HUMAN_REVIEW, config={"audience": "bank"}), state)

    created = [arg for name, arg in calls if name == CREATE_HUMAN_TASK_ACTIVITY]
    expect(created).to(have_length(1))
    expect(_transitions(calls)).to(equal([]))


async def test_extraction_gate__review_reject_terminates(monkeypatch):
    # Un rechazo en la rama review NO puede dejar seguir el caso a analyze/deliver.
    calls: list = []
    payload = {"caseId": str(_CASE), "taskId": str(_TASK_ID), "items": [_gate_item()]}
    _patch(
        monkeypatch,
        calls,
        {
            pp.EVALUATE_ACTIVATION_GATE_ACTIVITY: EvaluateActivationGateOutput(items=[_gate_item()]),
            OPEN_APPROVAL_TASK_ACTIVITY: OpenCaseTaskOutput(task_id=_TASK_ID, payload=payload),
        },
    )
    state = _state(policies=_activation("review"))
    ctx = ProcessingJobWorkflowBase()
    ctx._resolved_tasks["run-1:gate"] = {"approved": False, "comment": "ilegible"}

    await pp.extraction_gate(ctx, PhaseSpec(id="gate", kind=PhaseKind.EXTRACTION_GATE), state)

    expect(_transitions(calls)).to(equal(["NEEDS_REVIEW", "REJECTED"]))
    events = [arg for name, arg in calls if name == APPEND_CASE_EVENT_ACTIVITY]
    expect([e.type for e in events]).to(equal(["review.rejected"]))
    expect(events[0].payload["comment"]).to(equal("ilegible"))
    expect(events[0].dedupe_key).to(equal("run-1:gate:review.rejected"))
    expect(state.terminated).to(be_true)


# ─── _run_reanalysis · phases-config H1/H2 config round-trip ──────────────────


def _patch_reanalysis(monkeypatch, child_calls: list) -> None:
    async def fake_execute_activity(name, arg=None, **kwargs):
        return CreateAnalysisRunForPipelineOutput(run_id=arg.run_id, created=True)

    async def fake_execute_child_workflow(name, arg=None, **kwargs):
        child_calls.append((name, arg))

    monkeypatch.setattr(tw, "execute_activity", fake_execute_activity)
    monkeypatch.setattr(tw, "execute_child_workflow", fake_execute_child_workflow)
    monkeypatch.setattr(tw, "uuid4", lambda: UUID("77777777-7777-7777-7777-777777777777"))
    monkeypatch.setattr(tw, "logger", SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None))


async def test_run_reanalysis__forwards_sealed_providers_and_rule_set(monkeypatch):
    # El re-analyze por corrections debe reproducir la config sellada por analyze
    # (sin esto, las re-corridas revertían a env providers + TODAS las reglas).
    child_calls: list = []
    _patch_reanalysis(monkeypatch, child_calls)
    state = _state()
    state.put_artifact(
        "analysis_run",
        {
            "run_id": "old-run",
            "providers": {"parser": "anthropic", "reviewer": "openai:gpt-4o", "critic": None, "synthesizer": "gemini"},
            "rule_set": "high_risk",
        },
    )

    result = await pp._run_reanalysis(state)

    expect(result).to(equal("77777777-7777-7777-7777-777777777777"))
    expect(child_calls).to(have_length(1))
    _, child_input = child_calls[0]
    expect(child_input.rule_set).to(equal("high_risk"))
    expect(child_input.providers.parser).to(equal("anthropic"))
    expect(child_input.providers.reviewer).to(equal("openai:gpt-4o"))
    expect(child_input.providers.synthesizer).to(equal("gemini"))


async def test_run_reanalysis__defaults_when_artifact_missing(monkeypatch):
    # Runs en vuelo previos al fix (artifact sin la config) ⇒ defaults = env
    # providers + todas las reglas, idéntico al comportamiento anterior.
    child_calls: list = []
    _patch_reanalysis(monkeypatch, child_calls)
    state = _state()  # sin artifact analysis_run

    await pp._run_reanalysis(state)

    expect(child_calls).to(have_length(1))
    _, child_input = child_calls[0]
    expect(child_input.rule_set).to(be_none)
    expect(child_input.providers.parser).to(be_none)
    expect(child_input.providers.reviewer).to(be_none)
