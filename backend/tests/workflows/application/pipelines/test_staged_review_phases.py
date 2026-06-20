"""E5 · diseño §3.1/§3.3: human_review multinivel (stages L1/L2) + corrections.

Mismo harness que ``test_case_pause_phases.py``: ``temporalio.workflow``
monkeypatcheado y handler invocado directo con un ``ProcessingJobWorkflowBase``
real (incluye ``wait_for_task_or_corrections`` y ``_pending_corrections``).
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

from expects import be_false, be_none, be_true, equal, expect, have_length
from temporalio import workflow as tw

from src.common.domain.entities.workflows.case_runtime import (
    BuildStageGateItemsOutput,
    CheckBlockingResultsOutput,
    OpenCaseTaskOutput,
)
from src.common.domain.entities.workflows.document_processing import DocumentProcessingInput
from src.common.domain.enums.pipelines import PhaseKind
from src.common.domain.enums.webhooks import WebhookEventType
from src.workflows.application.pipelines import pause_phases as pp
from src.workflows.application.pipelines.case_transitions import (
    APPEND_CASE_EVENT_ACTIVITY,
    TRANSITION_CASE_STATUS_ACTIVITY,
)
from src.workflows.application.pipelines.pause_phases import (
    ANALYSIS_RERUN_EVENT,
    BUILD_STAGE_GATE_ITEMS_ACTIVITY,
    CHECK_BLOCKING_RESULTS_ACTIVITY,
    CREATE_ANALYSIS_RUN_ACTIVITY,
    DISPATCH_CASE_EVENT_ACTIVITY,
    OPEN_APPROVAL_TASK_ACTIVITY,
)
from src.workflows.application.pipelines.runtime import PipelineState
from src.workflows.domain.models.pipeline import PhaseSpec
from src.workflows.presentation.workflows.base import ProcessingJobWorkflowBase

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")
_CASE = UUID("44444444-4444-4444-4444-444444444444")
_TASK_L1 = UUID("55555555-5555-5555-5555-555555555551")
_TASK_L2 = UUID("55555555-5555-5555-5555-555555555552")
_RERUN = UUID("66666666-6666-6666-6666-666666666666")

_PHASE = PhaseSpec(id="approval", kind=PhaseKind.HUMAN_REVIEW, config={"kind": "approval"})


def _policies(stages: list[dict], **extra) -> dict:
    activation = {"mode": "mandatory", "stages": stages}
    activation.update(extra)
    return {"activation": activation, "completeness": None}


def _state(policies: dict) -> PipelineState:
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
    state.scratch["policies"] = policies
    return state


def _patch(monkeypatch, calls: list, responses: dict, *, child_calls: list | None = None) -> None:
    async def fake_execute_activity(name, arg=None, **kwargs):
        calls.append((name, arg))
        canned = responses.get(name)
        if callable(canned):
            return canned(arg)
        return canned

    async def fake_wait_condition(predicate, *a, **k):
        return None

    async def fake_execute_child_workflow(name, arg=None, **kwargs):
        if child_calls is not None:
            child_calls.append((name, arg, kwargs))

    monkeypatch.setattr(tw, "execute_activity", fake_execute_activity)
    monkeypatch.setattr(tw, "wait_condition", fake_wait_condition)
    monkeypatch.setattr(tw, "execute_child_workflow", fake_execute_child_workflow)
    monkeypatch.setattr(tw, "uuid4", lambda: _RERUN)
    monkeypatch.setattr(tw, "info", lambda: SimpleNamespace(workflow_id="run-1", run_id="r1"))
    monkeypatch.setattr(
        tw, "logger", SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None)
    )


def _transitions(calls: list) -> list[str]:
    return [arg.to_status for name, arg in calls if name == TRANSITION_CASE_STATUS_ACTIVITY]


def _events(calls: list) -> list:
    return [arg for name, arg in calls if name == APPEND_CASE_EVENT_ACTIVITY]


def _dispatches(calls: list) -> list:
    return [arg for name, arg in calls if name == DISPATCH_CASE_EVENT_ACTIVITY]


def _opened(calls: list) -> list:
    return [arg for name, arg in calls if name == OPEN_APPROVAL_TASK_ACTIVITY]


def _stage_payload(task_id: UUID, stage: str) -> dict:
    return {
        "caseId": str(_CASE),
        "taskId": str(task_id),
        "stage": stage,
        "verdict": "REVIEW",
        "summary": {"confidenceScore": 0.8},
        "items": [],
        "resolveUrl": f"/v1/tasks/{task_id}/resolve",
    }


def _open_by_stage(arg) -> OpenCaseTaskOutput:
    task_id = _TASK_L1 if arg.stage == "review_l1" else _TASK_L2
    return OpenCaseTaskOutput(task_id=task_id, payload=_stage_payload(task_id, arg.stage))


# ─── stages mandatory ────────────────────────────────────────────────────────


async def test_staged__both_mandatory_open_tasks_per_stage_and_complete(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {
            BUILD_STAGE_GATE_ITEMS_ACTIVITY: BuildStageGateItemsOutput(items=[]),
            OPEN_APPROVAL_TASK_ACTIVITY: _open_by_stage,
        },
    )
    state = _state(
        _policies([{"stage": "review_l1", "mode": "mandatory"}, {"stage": "review_l2", "mode": "mandatory"}])
    )
    ctx = ProcessingJobWorkflowBase()
    ctx._resolved_tasks["run-1:approval:review_l1"] = {"approved": True, "resolvedBy": "staff:s1"}
    ctx._resolved_tasks["run-1:approval:review_l2"] = {"approved": True, "resolvedBy": "user:u1"}

    await pp.human_review(ctx, _PHASE, state)

    opened = _opened(calls)
    expect(opened).to(have_length(2))
    expect(opened[0].task_key).to(equal("run-1:approval:review_l1"))
    expect(opened[0].stage).to(equal("review_l1"))
    expect(opened[0].audience).to(equal("doxiq_analyst"))
    expect(opened[1].task_key).to(equal("run-1:approval:review_l2"))
    expect(opened[1].stage).to(equal("review_l2"))
    expect(opened[1].audience).to(equal("tenant_analyst"))

    # REVIEW_L1 → REVIEW_L2 → PROCESSING (aprobación final reanuda el tail).
    expect(_transitions(calls)).to(equal(["REVIEW_L1", "REVIEW_L2", "PROCESSING"]))
    events = _events(calls)
    expect([e.type for e in events]).to(equal(["review.approved", "review.approved"]))
    expect(events[0].payload["stage"]).to(equal("review_l1"))
    expect(events[0].payload["actor"]).to(equal("staff:s1"))
    expect(events[1].payload["stage"]).to(equal("review_l2"))

    dispatches = _dispatches(calls)
    expect([d.event_type for d in dispatches]).to(
        equal(
            [
                WebhookEventType.CASE_NEEDS_REVIEW.value,
                WebhookEventType.CASE_NEEDS_REVIEW.value,
                WebhookEventType.CASE_REVIEW_COMPLETED.value,
            ]
        )
    )
    expect(dispatches[0].payload["stage"]).to(equal("review_l1"))
    completed = dispatches[2]
    expect(completed.task_id).to(equal(_TASK_L2))
    expect(completed.payload["corrections"]).to(equal(0))
    expect([s["outcome"] for s in completed.payload["stages"]]).to(equal(["approved", "approved"]))
    expect(state.terminated).to(be_false)
    expect(state.artifact("approval")["approved"]).to(be_true)


# ─── by_exception: skip + activación por gate items ──────────────────────────


async def test_staged__by_exception_without_signals_skips_stage_with_event(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {
            BUILD_STAGE_GATE_ITEMS_ACTIVITY: BuildStageGateItemsOutput(items=[]),
            CHECK_BLOCKING_RESULTS_ACTIVITY: CheckBlockingResultsOutput(blocking=False),
            OPEN_APPROVAL_TASK_ACTIVITY: _open_by_stage,
        },
    )
    state = _state(
        _policies(
            [{"stage": "review_l1", "mode": "by_exception"}, {"stage": "review_l2", "mode": "mandatory"}],
            sample_rate=0,
        )
    )
    ctx = ProcessingJobWorkflowBase()
    ctx._resolved_tasks["run-1:approval:review_l2"] = {"approved": True}

    await pp.human_review(ctx, _PHASE, state)

    events = _events(calls)
    expect([e.type for e in events]).to(equal(["review.skipped", "review.approved"]))
    expect(events[0].payload).to(equal({"mode": "by_exception", "stage": "review_l1"}))
    expect(events[0].dedupe_key).to(equal("run-1:approval:review_l1:review.skipped"))
    # Solo el L2 abre tarea y transiciona (L1 skipped: ANALYZING→REVIEW_L2).
    expect(_opened(calls)).to(have_length(1))
    expect(_transitions(calls)).to(equal(["REVIEW_L2", "PROCESSING"]))
    completed = _dispatches(calls)[-1]
    expect(completed.event_type).to(equal(WebhookEventType.CASE_REVIEW_COMPLETED.value))
    expect([s["outcome"] for s in completed.payload["stages"]]).to(equal(["skipped", "approved"]))


async def test_staged__by_exception_with_open_gate_items_activates(monkeypatch):
    calls: list = []
    item = {"documentId": str(uuid4()), "fieldPath": "total"}
    _patch(
        monkeypatch,
        calls,
        {
            BUILD_STAGE_GATE_ITEMS_ACTIVITY: BuildStageGateItemsOutput(items=[item]),
            CHECK_BLOCKING_RESULTS_ACTIVITY: CheckBlockingResultsOutput(blocking=False),
            OPEN_APPROVAL_TASK_ACTIVITY: _open_by_stage,
        },
    )
    state = _state(_policies([{"stage": "review_l1", "mode": "by_exception"}], sample_rate=0))
    ctx = ProcessingJobWorkflowBase()
    ctx._resolved_tasks["run-1:approval:review_l1"] = {"approved": True}

    await pp.human_review(ctx, _PHASE, state)

    opened = _opened(calls)
    expect(opened).to(have_length(1))
    expect(opened[0].gate_items).to(equal([item]))
    expect(_transitions(calls)).to(equal(["REVIEW_L1", "PROCESSING"]))


async def test_staged__all_stages_skipped_still_emits_completed_without_transition(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {
            BUILD_STAGE_GATE_ITEMS_ACTIVITY: BuildStageGateItemsOutput(items=[]),
            CHECK_BLOCKING_RESULTS_ACTIVITY: CheckBlockingResultsOutput(blocking=False),
        },
    )
    state = _state(_policies([{"stage": "review_l2", "mode": "by_exception"}], sample_rate=0))
    ctx = ProcessingJobWorkflowBase()

    await pp.human_review(ctx, _PHASE, state)

    expect(_transitions(calls)).to(equal([]))
    completed = _dispatches(calls)[-1]
    expect(completed.event_type).to(equal(WebhookEventType.CASE_REVIEW_COMPLETED.value))
    expect(completed.task_id).to(be_none)
    expect(state.artifact("approval")["activated"]).to(be_false)


# ─── filtro Rossum (L2 excluye verification.level >= 1) ──────────────────────


async def test_staged__l2_gate_items_request_excludes_verified_level_1(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {
            BUILD_STAGE_GATE_ITEMS_ACTIVITY: BuildStageGateItemsOutput(items=[]),
            OPEN_APPROVAL_TASK_ACTIVITY: _open_by_stage,
        },
    )
    state = _state(
        _policies([{"stage": "review_l1", "mode": "mandatory"}, {"stage": "review_l2", "mode": "mandatory"}])
    )
    ctx = ProcessingJobWorkflowBase()
    ctx._resolved_tasks["run-1:approval:review_l1"] = {"approved": True}
    ctx._resolved_tasks["run-1:approval:review_l2"] = {"approved": True}

    await pp.human_review(ctx, _PHASE, state)

    builds = [arg for name, arg in calls if name == BUILD_STAGE_GATE_ITEMS_ACTIVITY]
    expect(builds).to(have_length(2))
    expect(builds[0].exclude_verified_level).to(be_none)  # L1: sin filtro
    expect(builds[1].exclude_verified_level).to(equal(1))  # L2: filtro Rossum


# ─── rechazo por stage ───────────────────────────────────────────────────────


async def test_staged__rejection_at_l2_transitions_rejected_and_terminates(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {
            BUILD_STAGE_GATE_ITEMS_ACTIVITY: BuildStageGateItemsOutput(items=[]),
            OPEN_APPROVAL_TASK_ACTIVITY: _open_by_stage,
        },
    )
    state = _state(
        _policies([{"stage": "review_l1", "mode": "mandatory"}, {"stage": "review_l2", "mode": "mandatory"}])
    )
    ctx = ProcessingJobWorkflowBase()
    ctx._resolved_tasks["run-1:approval:review_l1"] = {"approved": True}
    ctx._resolved_tasks["run-1:approval:review_l2"] = {"approved": False, "comment": "no cuadra"}

    await pp.human_review(ctx, _PHASE, state)

    expect(_transitions(calls)).to(equal(["REVIEW_L1", "REVIEW_L2", "REJECTED"]))
    events = _events(calls)
    expect([e.type for e in events]).to(equal(["review.approved", "review.rejected"]))
    expect(events[1].payload["stage"]).to(equal("review_l2"))
    expect(events[1].payload["comment"]).to(equal("no cuadra"))
    expect(events[1].dedupe_key).to(equal("run-1:approval:review_l2:review.rejected"))
    # NO case.review.completed tras un rechazo.
    dispatched_types = [d.event_type for d in _dispatches(calls)]
    expect(WebhookEventType.CASE_REVIEW_COMPLETED.value in dispatched_types).to(be_false)
    expect(state.terminated).to(be_true)
    expect(state.artifact("approval")["approved"]).to(be_false)


async def test_staged__rejection_at_l1_skips_l2_entirely(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {
            BUILD_STAGE_GATE_ITEMS_ACTIVITY: BuildStageGateItemsOutput(items=[]),
            OPEN_APPROVAL_TASK_ACTIVITY: _open_by_stage,
        },
    )
    state = _state(
        _policies([{"stage": "review_l1", "mode": "mandatory"}, {"stage": "review_l2", "mode": "mandatory"}])
    )
    ctx = ProcessingJobWorkflowBase()
    ctx._resolved_tasks["run-1:approval:review_l1"] = {"approved": False}

    await pp.human_review(ctx, _PHASE, state)

    expect(_transitions(calls)).to(equal(["REVIEW_L1", "REJECTED"]))
    expect(_opened(calls)).to(have_length(1))  # L2 jamás abre
    expect(state.terminated).to(be_true)


# ─── corrections → re-analyze → approve (§3.3) ───────────────────────────────


async def test_staged__corrections_trigger_reanalysis_then_approval_applies(monkeypatch):
    calls: list = []
    child_calls: list = []
    _patch(
        monkeypatch,
        calls,
        {
            BUILD_STAGE_GATE_ITEMS_ACTIVITY: BuildStageGateItemsOutput(items=[]),
            CHECK_BLOCKING_RESULTS_ACTIVITY: CheckBlockingResultsOutput(blocking=False),
            OPEN_APPROVAL_TASK_ACTIVITY: _open_by_stage,
            CREATE_ANALYSIS_RUN_ACTIVITY: None,
        },
        child_calls=child_calls,
    )
    state = _state(_policies([{"stage": "review_l1", "mode": "mandatory"}]))
    ctx = ProcessingJobWorkflowBase()
    task_key = "run-1:approval:review_l1"
    # La corrección Y la aprobación llegan juntas: la corrección se procesa
    # PRIMERO (re-analyze) y la aprobación se aplica DESPUÉS (invariante §3.3).
    ctx._pending_corrections[task_key] = [{"fields": [{"documentId": "d1", "fieldPath": "total"}]}]
    ctx._resolved_tasks[task_key] = {"approved": True}

    await pp.human_review(ctx, _PHASE, state)

    # Re-analyze: run nuevo + child workflow (TODAS las reglas del caso).
    creates = [arg for name, arg in calls if name == CREATE_ANALYSIS_RUN_ACTIVITY]
    expect(creates).to(have_length(1))
    expect(str(creates[0].run_id)).to(equal(str(_RERUN)))
    expect(child_calls).to(have_length(1))
    expect(child_calls[0][0]).to(equal("WorkflowAnalysisRunWorkflow"))

    events = _events(calls)
    expect([e.type for e in events]).to(equal([ANALYSIS_RERUN_EVENT, "review.approved"]))
    expect(events[0].payload["runId"]).to(equal(str(_RERUN)))
    expect(events[0].payload["fields"]).to(equal(1))
    expect(events[0].dedupe_key).to(equal(f"{task_key}:{ANALYSIS_RERUN_EVENT}:{_RERUN}"))

    # Tras el re-analyze los gate items del stage se refrescan (2ª build).
    builds = [arg for name, arg in calls if name == BUILD_STAGE_GATE_ITEMS_ACTIVITY]
    expect(builds).to(have_length(2))

    completed = _dispatches(calls)[-1]
    expect(completed.event_type).to(equal(WebhookEventType.CASE_REVIEW_COMPLETED.value))
    expect(completed.payload["corrections"]).to(equal(1))
    expect(state.terminated).to(be_false)


# ─── compat E4 ───────────────────────────────────────────────────────────────


async def test_staged__policy_without_stages_keeps_e4_single_gate(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {
            OPEN_APPROVAL_TASK_ACTIVITY: OpenCaseTaskOutput(
                task_id=_TASK_L1,
                payload={"caseId": str(_CASE), "taskId": str(_TASK_L1)},
            ),
        },
    )
    state = _state({"activation": {"mode": "mandatory"}, "completeness": None})
    ctx = ProcessingJobWorkflowBase()
    ctx._resolved_tasks["run-1:approval"] = {"approved": True}

    await pp.human_review(ctx, _PHASE, state)

    # E4 intacto: task_key SIN sufijo, NEEDS_REVIEW, sin stage, sin webhook
    # case.review.completed.
    opened = _opened(calls)
    expect(opened).to(have_length(1))
    expect(opened[0].task_key).to(equal("run-1:approval"))
    expect(opened[0].stage).to(be_none)
    expect(_transitions(calls)).to(equal(["NEEDS_REVIEW"]))
    dispatched_types = [d.event_type for d in _dispatches(calls)]
    expect(dispatched_types).to(equal([WebhookEventType.CASE_NEEDS_REVIEW.value]))
