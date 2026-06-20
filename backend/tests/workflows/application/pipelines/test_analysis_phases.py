"""Unit tests de las fases case-scope del intérprete (E2 · analyze/output/deliver).

Mismo harness que la suite de regresión E1: se monkeypatchea
``temporalio.workflow`` (activities, child workflow, uuid4, logger) y se invoca
el handler registrado en ``PHASE_LIBRARY`` directamente. Cubre:

- skip limpio de las tres fases cuando el run no tiene caso (uploads STANDARD),
- el happy path de ``analyze`` (create_analysis_run + child ABANDON + artifact),
- el camino de fallo del child (mark_failed + ``case.failed`` + error terminal),
- ``output`` (artifact compacto / ``pipeline.output_failed``) y ``deliver``
  (``case.output.ready`` + artifact delivery).
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from expects import be_none, equal, expect, have_keys, have_length
from temporalio import workflow as tw
from temporalio.exceptions import ActivityError, ApplicationError, ChildWorkflowError
from temporalio.workflow import ParentClosePolicy

from src.common.domain.entities.workflows.analysis_run_processing import (
    BuildCaseOutputInput,
    BuildCaseOutputOutput,
    CreateAnalysisRunForPipelineInput,
    DispatchCaseEventInput,
    MarkAnalysisRunFailedInput,
)
from src.common.domain.enums.pipelines import PhaseKind
from src.common.domain.enums.webhooks import WebhookEventType
from src.workflows.application.pipelines import (
    analysis_phases,  # noqa: F401 — side effect requerido: puebla PHASE_LIBRARY
)
from src.workflows.application.pipelines.analysis_phases import (
    ANALYSIS_CHILD_WORKFLOW,
    BUILD_CASE_OUTPUT_ACTIVITY,
    CREATE_ANALYSIS_RUN_ACTIVITY,
    DISPATCH_CASE_EVENT_ACTIVITY,
    MARK_ANALYSIS_RUN_FAILED_ACTIVITY,
    OPEN_QA_AUDIT_TASK_ACTIVITY,
    _qa_sample_rate,
    _qa_sampled,
)
from src.workflows.application.pipelines.case_transitions import (
    TRANSITION_CASE_STATUS_ACTIVITY,
)
from src.workflows.application.pipelines.runtime import PHASE_LIBRARY, PipelineState
from src.workflows.domain.models.pipeline import PhaseSpec

_RUN_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")

_ANALYZE = PHASE_LIBRARY[PhaseKind.ANALYZE.value]
_OUTPUT = PHASE_LIBRARY[PhaseKind.OUTPUT.value]
_DELIVER = PHASE_LIBRARY[PhaseKind.DELIVER.value]


def _case_state(**overrides) -> PipelineState:
    data = SimpleNamespace(
        persist=True,
        case_id=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
    )
    for key, value in overrides.items():
        setattr(data, key, value)
    return PipelineState(data=data, job_id="JOB-E2")


def _phase(kind: PhaseKind) -> PhaseSpec:
    return PhaseSpec(id=kind.value, kind=kind)


def _patch_runtime(
    monkeypatch,
    activities: list,
    children: list,
    *,
    canned=None,
    activity_error_for: str | None = None,
    child_error: Exception | None = None,
) -> None:
    """Stub determinista de ``temporalio.workflow`` para correr handlers directo."""

    async def fake_execute_activity(name, arg=None, **kwargs):
        if name == activity_error_for:
            raise _activity_error()
        activities.append((name, arg))
        return canned(name, arg) if canned else None

    async def fake_execute_child_workflow(name, arg=None, **kwargs):
        children.append((name, arg, kwargs))
        if child_error is not None:
            raise child_error
        return None

    monkeypatch.setattr(tw, "execute_activity", fake_execute_activity)
    monkeypatch.setattr(tw, "execute_child_workflow", fake_execute_child_workflow)
    monkeypatch.setattr(tw, "uuid4", lambda: _RUN_ID)
    # E6: el hook QA lee ``workflow.info().workflow_id`` para el task_key.
    monkeypatch.setattr(tw, "info", lambda: SimpleNamespace(workflow_id=f"wf-{_RUN_ID}"))
    monkeypatch.setattr(tw, "logger", SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None))


def _child_workflow_error(cause_message: str = "rule evaluation exploded") -> ChildWorkflowError:
    error = ChildWorkflowError(
        "child workflow failed",
        namespace="default",
        workflow_id=f"analysis-run-{_RUN_ID}",
        run_id="run-x",
        workflow_type=ANALYSIS_CHILD_WORKFLOW,
        initiated_event_id=1,
        started_event_id=2,
        retry_state=None,
    )
    error.__cause__ = ApplicationError(cause_message)
    return error


def _activity_error() -> ActivityError:
    error = ActivityError(
        "activity failed",
        scheduled_event_id=1,
        started_event_id=2,
        identity="worker",
        activity_type=BUILD_CASE_OUTPUT_ACTIVITY,
        activity_id="1",
        retry_state=None,
    )
    error.__cause__ = ApplicationError("synthesis blew up")
    return error


# ─── analyze ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("overrides", [{"case_id": None}, {"persist": False}, {"tenant_id": None}])
async def test_analyze__without_case_skips_clean_without_activities(monkeypatch, overrides):
    # Arrange
    activities: list = []
    children: list = []
    _patch_runtime(monkeypatch, activities, children)
    state = _case_state(**overrides)

    # Act
    await _ANALYZE(SimpleNamespace(), _phase(PhaseKind.ANALYZE), state)

    # Assert — artifact de skip y CERO side-effects
    expect(state.artifact("analysis_run")).to(equal({"skipped": True, "reason": "no_case"}))
    expect(activities).to(have_length(0))
    expect(children).to(have_length(0))


async def test_analyze__happy_path_creates_run_and_launches_abandoned_child(monkeypatch):
    # Arrange
    activities: list = []
    children: list = []
    _patch_runtime(monkeypatch, activities, children)
    state = _case_state()

    # Act
    await _ANALYZE(SimpleNamespace(), _phase(PhaseKind.ANALYZE), state)

    # Assert — E4: el caso transiciona PROCESSING→ANALYZING al arrancar la fase
    transitions = [arg for name, arg in activities if name == TRANSITION_CASE_STATUS_ACTIVITY]
    expect([t.to_status for t in transitions]).to(equal(["PROCESSING", "ANALYZING"]))

    # Assert — la activity de creación recibe el run_id determinista del workflow
    creates = [(name, arg) for name, arg in activities if name == CREATE_ANALYSIS_RUN_ACTIVITY]
    expect(creates).to(have_length(1))
    name, arg = creates[0]
    expect(name).to(equal(CREATE_ANALYSIS_RUN_ACTIVITY))
    expect(type(arg)).to(equal(CreateAnalysisRunForPipelineInput))
    expect(arg.run_id).to(equal(_RUN_ID))
    expect(arg.tenant_id).to(equal(state.data.tenant_id))
    expect(arg.workflow_id).to(equal(state.data.workflow_id))
    expect(arg.case_id).to(equal(state.data.case_id))

    # Assert — child workflow con id estable y ParentClosePolicy.ABANDON
    expect(children).to(have_length(1))
    child_name, child_arg, child_kwargs = children[0]
    expect(child_name).to(equal(ANALYSIS_CHILD_WORKFLOW))
    expect(child_arg.run_id).to(equal(_RUN_ID))
    expect(child_arg.case_id).to(equal(state.data.case_id))
    expect(child_kwargs["id"]).to(equal(f"analysis-run-{_RUN_ID}"))
    expect(child_kwargs["parent_close_policy"]).to(equal(ParentClosePolicy.ABANDON))

    # Assert — artifact con el run_id + config sellada (providers/rule_set) para
    # las fases output/deliver y el re-analyze por corrections (H1/H2).
    expect(state.artifact("analysis_run")).to(
        equal(
            {
                "run_id": str(_RUN_ID),
                "providers": {"parser": None, "reviewer": None, "critic": None, "synthesizer": None},
                "rule_set": None,
            }
        )
    )


async def test_analyze__child_failure_marks_run_failed_dispatches_case_failed_and_raises_terminal(monkeypatch):
    # Arrange
    activities: list = []
    children: list = []
    _patch_runtime(monkeypatch, activities, children, child_error=_child_workflow_error("regla 7 explotó"))
    state = _case_state()

    # Act
    with pytest.raises(ApplicationError) as exc_info:
        await _ANALYZE(SimpleNamespace(), _phase(PhaseKind.ANALYZE), state)

    # Assert — error terminal del pipeline, no reintentable
    expect(exc_info.value.type).to(equal("pipeline.analyze_failed"))
    expect(exc_info.value.non_retryable).to(equal(True))

    # Assert — safety net: la fila del run se marca FAILED con la causa del child
    by_name = {name: arg for name, arg in activities}
    mark = by_name[MARK_ANALYSIS_RUN_FAILED_ACTIVITY]
    expect(type(mark)).to(equal(MarkAnalysisRunFailedInput))
    expect(mark.run_id).to(equal(_RUN_ID))
    expect(mark.error).to(equal("regla 7 explotó"))

    # Assert — checkpoint case.failed al outbox con el código de la fase
    dispatch = by_name[DISPATCH_CASE_EVENT_ACTIVITY]
    expect(type(dispatch)).to(equal(DispatchCaseEventInput))
    expect(dispatch.event_type).to(equal(WebhookEventType.CASE_FAILED.value))
    expect(dispatch.run_id).to(equal(_RUN_ID))
    expect(dispatch.error).to(have_keys({"code": "pipeline.analyze_failed", "message": "regla 7 explotó"}))

    # Assert — sin artifact analysis_run: las fases siguientes skipearían
    expect(state.artifact("analysis_run")).to(be_none)


# ─── output ──────────────────────────────────────────────────────────────────


async def test_output__skips_when_analysis_run_skipped(monkeypatch):
    # Arrange
    activities: list = []
    _patch_runtime(monkeypatch, activities, [])
    state = _case_state()
    state.put_artifact("analysis_run", {"skipped": True, "reason": "no_case"})

    # Act
    await _OUTPUT(SimpleNamespace(), _phase(PhaseKind.OUTPUT), state)

    # Assert
    expect(state.artifact("case_output")).to(equal({"skipped": True, "reason": "no_analysis_run"}))
    expect(activities).to(have_length(0))


async def test_output__skips_when_run_has_no_case(monkeypatch):
    # Arrange — defensa en profundidad: sin caso skipea aunque haya artifact
    activities: list = []
    _patch_runtime(monkeypatch, activities, [])
    state = _case_state(case_id=None)
    state.put_artifact("analysis_run", {"run_id": str(_RUN_ID)})

    # Act
    await _OUTPUT(SimpleNamespace(), _phase(PhaseKind.OUTPUT), state)

    # Assert
    expect(state.artifact("case_output")).to(equal({"skipped": True, "reason": "no_analysis_run"}))
    expect(activities).to(have_length(0))


async def test_output__happy_path_builds_case_output_and_records_compact_artifact(monkeypatch):
    # Arrange
    result = BuildCaseOutputOutput(
        run_id=_RUN_ID,
        verdict="APPROVED",
        narrative_status="COMPLETED",
        has_output=True,
        document_outputs=2,
        warnings=[],
    )
    activities: list = []
    _patch_runtime(monkeypatch, activities, [], canned=lambda name, arg: result)
    state = _case_state()
    state.put_artifact("analysis_run", {"run_id": str(_RUN_ID)})

    # Act
    await _OUTPUT(SimpleNamespace(), _phase(PhaseKind.OUTPUT), state)

    # Assert — la activity recibe el contexto completo del caso
    expect(activities).to(have_length(1))
    name, arg = activities[0]
    expect(name).to(equal(BUILD_CASE_OUTPUT_ACTIVITY))
    expect(type(arg)).to(equal(BuildCaseOutputInput))
    expect(arg.run_id).to(equal(_RUN_ID))
    expect(arg.case_id).to(equal(state.data.case_id))

    # Assert — artifact compacto (refs/metadata, nunca el output inline)
    expect(state.artifact("case_output")).to(equal(result.model_dump(mode="json")))


async def test_output__activity_failure_dispatches_case_failed_and_raises_terminal(monkeypatch):
    # Arrange
    activities: list = []
    _patch_runtime(monkeypatch, activities, [], activity_error_for=BUILD_CASE_OUTPUT_ACTIVITY)
    state = _case_state()
    state.put_artifact("analysis_run", {"run_id": str(_RUN_ID)})

    # Act
    with pytest.raises(ApplicationError) as exc_info:
        await _OUTPUT(SimpleNamespace(), _phase(PhaseKind.OUTPUT), state)

    # Assert — error terminal con el código de la fase output
    expect(exc_info.value.type).to(equal("pipeline.output_failed"))
    expect(exc_info.value.non_retryable).to(equal(True))

    # Assert — case.failed best-effort antes de propagar (+ transición FAILED E4)
    transitions = [arg for name, arg in activities if name == TRANSITION_CASE_STATUS_ACTIVITY]
    expect([t.to_status for t in transitions]).to(equal(["FAILED"]))
    dispatches = [arg for name, arg in activities if name == DISPATCH_CASE_EVENT_ACTIVITY]
    expect(dispatches).to(have_length(1))
    dispatch = dispatches[0]
    expect(dispatch.event_type).to(equal(WebhookEventType.CASE_FAILED.value))
    expect(dispatch.error["code"]).to(equal("pipeline.output_failed"))
    expect(state.artifact("case_output")).to(be_none)


# ─── deliver ─────────────────────────────────────────────────────────────────


async def test_deliver__skips_when_case_output_skipped(monkeypatch):
    # Arrange
    activities: list = []
    _patch_runtime(monkeypatch, activities, [])
    state = _case_state()
    state.put_artifact("case_output", {"skipped": True, "reason": "no_analysis_run"})

    # Act
    await _DELIVER(SimpleNamespace(), _phase(PhaseKind.DELIVER), state)

    # Assert — ni evento ni artifact delivery
    expect(activities).to(have_length(0))
    expect(state.artifact("delivery")).to(be_none)


async def test_deliver__happy_path_dispatches_case_output_ready_and_records_artifact(monkeypatch):
    # Arrange — el dispatch reporta 2 destinos entregados
    activities: list = []
    _patch_runtime(monkeypatch, activities, [], canned=lambda name, arg: 2)
    state = _case_state()
    state.put_artifact("case_output", {"run_id": str(_RUN_ID), "verdict": "APPROVED"})

    # Act
    await _DELIVER(SimpleNamespace(), _phase(PhaseKind.DELIVER), state)

    # Assert — evento case.output.ready con el run del artifact case_output
    dispatches = [arg for name, arg in activities if name == DISPATCH_CASE_EVENT_ACTIVITY]
    expect(dispatches).to(have_length(1))
    arg = dispatches[0]
    expect(type(arg)).to(equal(DispatchCaseEventInput))
    expect(arg.event_type).to(equal(WebhookEventType.CASE_OUTPUT_READY.value))
    expect(arg.run_id).to(equal(_RUN_ID))
    expect(arg.case_id).to(equal(state.data.case_id))

    # Assert — E4: tras entregar, el caso queda COMPLETED
    transitions = [arg for name, arg in activities if name == TRANSITION_CASE_STATUS_ACTIVITY]
    expect([t.to_status for t in transitions]).to(equal(["COMPLETED"]))

    # Assert — artifact delivery con el conteo de destinos
    expect(state.artifact("delivery")).to(equal({"event": WebhookEventType.CASE_OUTPUT_READY.value, "dispatched": 2}))


# ─── QA sampling post-COMPLETED (E6 · §3) ─────────────────────────────────────


def test_qa_sampled__rate_zero_never_samples():
    # Default: rate 0 ⇒ ningún caso entra a la auditoría QA.
    expect(_qa_sampled(str(uuid4()), 0.0)).to(equal(False))


def test_qa_sampled__rate_one_always_samples():
    # rate 1 ⇒ todos los casos auto-aprobados se auditan.
    for _ in range(20):
        expect(_qa_sampled(str(uuid4()), 1.0)).to(equal(True))


def test_qa_sampled__is_deterministic_per_case_id():
    # La MISMA clave (case_id) cae siempre igual ⇒ re-runs no cambian el veredicto.
    case_id = str(uuid4())
    expect(_qa_sampled(case_id, 0.5)).to(equal(_qa_sampled(case_id, 0.5)))


def test_qa_sample_rate__reads_sealed_policy():
    state = _case_state()
    state.scratch["policies"] = {"activation": {"qa_sample_rate": 0.42}}

    expect(_qa_sample_rate(state)).to(equal(0.42))


def test_qa_sample_rate__defaults_to_zero_without_policy():
    expect(_qa_sample_rate(_case_state())).to(equal(0.0))


async def test_deliver__channels_config_flows_into_dispatch_input(monkeypatch):
    # phases-config · deliver.channels: el allowlist viaja al DispatchCaseEventInput.
    activities: list = []
    _patch_runtime(monkeypatch, activities, [], canned=lambda name, arg: 1)
    state = _case_state()
    state.put_artifact("case_output", {"run_id": str(_RUN_ID)})

    await _DELIVER(
        SimpleNamespace(),
        PhaseSpec(id="deliver", kind=PhaseKind.DELIVER, config={"channels": ["dest-a", "dest-b"]}),
        state,
    )

    dispatches = [arg for name, arg in activities if name == DISPATCH_CASE_EVENT_ACTIVITY]
    expect(dispatches[0].channels).to(equal(["dest-a", "dest-b"]))


async def test_deliver__qa_rate_zero_does_not_open_qa_task(monkeypatch):
    # Arrange — sin policy QA (default 0): la entrega NO dispara la auditoría.
    activities: list = []
    _patch_runtime(monkeypatch, activities, [], canned=lambda name, arg: 1)
    state = _case_state()
    state.put_artifact("case_output", {"run_id": str(_RUN_ID)})

    # Act
    await _DELIVER(SimpleNamespace(), _phase(PhaseKind.DELIVER), state)

    # Assert — ninguna llamada a la activity QA
    qa_calls = [arg for name, arg in activities if name == OPEN_QA_AUDIT_TASK_ACTIVITY]
    expect(qa_calls).to(have_length(0))


async def test_deliver__qa_rate_one_opens_qa_task_fire_and_forget(monkeypatch):
    # Arrange — qa_sample_rate=1 ⇒ el caso entra a la cola QA tras COMPLETED.
    from src.common.domain.entities.workflows.case_runtime import (
        OpenQaAuditTaskInput,
        OpenQaAuditTaskOutput,
    )

    activities: list = []

    def _canned(name, arg):
        if name == OPEN_QA_AUDIT_TASK_ACTIVITY:
            return OpenQaAuditTaskOutput(task_id=uuid4(), created=True)
        return 1

    _patch_runtime(monkeypatch, activities, [], canned=_canned)
    state = _case_state()
    state.scratch["policies"] = {"activation": {"qa_sample_rate": 1.0}}
    state.put_artifact("case_output", {"run_id": str(_RUN_ID)})

    # Act
    await _DELIVER(SimpleNamespace(), _phase(PhaseKind.DELIVER), state)

    # Assert — la activity QA se invocó con el contexto del caso y el run
    qa_calls = [arg for name, arg in activities if name == OPEN_QA_AUDIT_TASK_ACTIVITY]
    expect(qa_calls).to(have_length(1))
    qa_arg = qa_calls[0]
    expect(type(qa_arg)).to(equal(OpenQaAuditTaskInput))
    expect(qa_arg.case_id).to(equal(state.data.case_id))
    expect(qa_arg.run_id).to(equal(str(_RUN_ID)))

    # Assert — el caso sigue COMPLETED (QA no toca el estado)
    transitions = [arg for name, arg in activities if name == TRANSITION_CASE_STATUS_ACTIVITY]
    expect([t.to_status for t in transitions]).to(equal(["COMPLETED"]))


async def test_deliver__qa_open_failure_never_breaks_completed_case(monkeypatch):
    # Arrange — la activity QA explota: el caso ya entregado NO debe fallar.
    activities: list = []

    async def fake_execute_activity(name, arg=None, **kwargs):
        activities.append((name, arg))
        if name == OPEN_QA_AUDIT_TASK_ACTIVITY:
            raise RuntimeError("qa queue down")
        return 1

    async def fake_execute_child_workflow(name, arg=None, **kwargs):
        return None

    monkeypatch.setattr(tw, "execute_activity", fake_execute_activity)
    monkeypatch.setattr(tw, "execute_child_workflow", fake_execute_child_workflow)
    monkeypatch.setattr(tw, "uuid4", lambda: _RUN_ID)
    monkeypatch.setattr(tw, "info", lambda: SimpleNamespace(workflow_id=f"wf-{_RUN_ID}"))
    monkeypatch.setattr(tw, "logger", SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None))
    state = _case_state()
    state.scratch["policies"] = {"activation": {"qa_sample_rate": 1.0}}
    state.put_artifact("case_output", {"run_id": str(_RUN_ID)})

    # Act — no levanta
    await _DELIVER(SimpleNamespace(), _phase(PhaseKind.DELIVER), state)

    # Assert — la entrega quedó registrada pese al fallo del QA
    expect(state.artifact("delivery")).to(equal({"event": WebhookEventType.CASE_OUTPUT_READY.value, "dispatched": 1}))
