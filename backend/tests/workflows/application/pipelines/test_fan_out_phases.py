"""E5 · diseño §2: fan-out a child cases en las fases del intérprete.

- ``classify_pages`` con ``fan_out: child_cases``: activity ``create_child_cases``
  (refs compactos) + case_event ``case.split`` (dedupe) + scratch para finalize.
  SIN la config, ni una activity nueva (los golden E1–E4 quedan byte-idénticos —
  lo prueba la suite de regresión).
- ``finalize`` con children en scratch: ``start_child_case_runs`` en batches de
  20 y señal ``case_split`` al padre (en vez del ``case_docs_changed`` E4).
- ``await_documents``: child auto-ready al primer docs_changed; padre con
  ``case_split`` sale del wait, queda PROCESSING y termina el run.
- ``validate_phases``: ``fan_out`` solo en classify_pages, modo válido, máximo > 0.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from expects import be_true, equal, expect, have_length
from temporalio import workflow as tw
from temporalio.exceptions import ApplicationError

from src.common.domain.entities.workflows.case_runtime import (
    ChildCaseRef,
    CreateChildCasesOutput,
    EvaluateCaseCompletenessOutput,
    MarkCaseReadyOutput,
    StartChildCaseRunsOutput,
)
from src.common.domain.entities.workflows.document_processing import DocumentProcessingInput
from src.common.domain.enums.pipelines import PhaseKind
from src.workflows.application.pipelines import (  # noqa: F401 — side effects: pueblan PHASE_LIBRARY
    extraction_phases,
    pause_phases,
)
from src.workflows.application.pipelines.case_transitions import (
    APPEND_CASE_EVENT_ACTIVITY,
    TRANSITION_CASE_STATUS_ACTIVITY,
)
from src.workflows.application.pipelines.extraction_phases import (
    CASE_SPLIT_EVENT,
    classify_pages,
    finalize,
)
from src.workflows.application.pipelines.pause_phases import (
    EVALUATE_CASE_COMPLETENESS_ACTIVITY,
    MARK_CASE_READY_ACTIVITY,
    await_documents,
)
from src.workflows.application.pipelines.runtime import PipelineState
from src.workflows.application.workflow_cases.case_run_starter import CASE_SPLIT_SIGNAL
from src.workflows.domain.models.pipeline import PhaseSpec
from src.workflows.domain.services.pipeline_validation import (
    InvalidPipelinePhasesError,
    validate_phases,
)
from src.workflows.presentation.workflows.activities.case_runtime_activities import (
    SIGNAL_CASE_WORKFLOW_ACTIVITY,
)
from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    ClassifiedDocumentRef,
    PersistClassifiedDocumentsOutput,
    PersistedDocumentRef,
    ReadClassifiedRefsOutput,
)
from src.workflows.presentation.workflows.activities.fan_out_cases import (
    CREATE_CHILD_CASES_ACTIVITY,
    START_CHILD_CASE_RUNS_ACTIVITY,
)
from src.workflows.presentation.workflows.base import (
    INVOKE_LAMBDA_ACTIVITY,
    READ_CLASSIFIED_REFS_ACTIVITY,
    ProcessingJobWorkflowBase,
)

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")
_CASE = UUID("44444444-4444-4444-4444-444444444444")
_FILE = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
_SET = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")


def _data() -> DocumentProcessingInput:
    return DocumentProcessingInput(
        object_key="s3://bucket/circular.pdf",
        document_types=[],
        job_id="JOB-1",
        case_id=_CASE,
        workflow_id=_WORKFLOW,
        tenant_id=_TENANT,
        file_id=_FILE,
        file_name="circular.pdf",
        processing_job_uuid=_SET,
        persist=True,
    )


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
    monkeypatch.setattr(tw, "now", lambda: datetime(2026, 6, 10, tzinfo=UTC))
    monkeypatch.setattr(tw, "uuid4", uuid4)
    monkeypatch.setattr(
        tw, "logger", SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None)
    )


def _classified(n: int) -> ReadClassifiedRefsOutput:
    return ReadClassifiedRefsOutput(
        documents=[
            ClassifiedDocumentRef(document_index=i, document_type_name="Persona")
            for i in range(n)
        ]
    )


def _persisted(n: int) -> PersistClassifiedDocumentsOutput:
    return PersistClassifiedDocumentsOutput(
        documents=[
            PersistedDocumentRef(
                document_id=uuid4(), document_type_name="Persona", document_index=i
            )
            for i in range(n)
        ]
    )


def _children_output(n: int) -> CreateChildCasesOutput:
    return CreateChildCasesOutput(
        children=[
            ChildCaseRef(case_id=uuid4(), document_index=i, external_ref=f"CIRC-{i + 1:03d}")
            for i in range(n)
        ],
        created=n,
    )


def _classify_responses(n_docs: int, children: CreateChildCasesOutput | None = None) -> dict:
    from src.workflows.presentation.workflows.base import PERSIST_CLASSIFIED_DOCS_ACTIVITY

    responses = {
        INVOKE_LAMBDA_ACTIVITY: {"output_uri": "s3://bucket/classify.json"},
        READ_CLASSIFIED_REFS_ACTIVITY: _classified(n_docs),
        PERSIST_CLASSIFIED_DOCS_ACTIVITY: _persisted(n_docs),
    }
    if children is not None:
        responses[CREATE_CHILD_CASES_ACTIVITY] = children
    return responses


def _classify_state() -> PipelineState:
    state = PipelineState(data=_data(), job_id="JOB-1")
    state.extract_text = {"output_uri": "s3://bucket/text.json"}
    state.scratch["run_scope"] = "document"
    return state


# ─── classify_pages · rama fan_out ───────────────────────────────────────────


async def test_classify_pages__fan_out_creates_children_and_appends_case_split(monkeypatch):
    calls: list = []
    children = _children_output(3)
    _patch(monkeypatch, calls, _classify_responses(3, children))
    state = _classify_state()
    phase = PhaseSpec(
        id="classify", kind=PhaseKind.CLASSIFY_PAGES, config={"fan_out": "child_cases"}
    )

    await classify_pages(ProcessingJobWorkflowBase(), phase, state)

    creates = [arg for name, arg in calls if name == CREATE_CHILD_CASES_ACTIVITY]
    expect(creates).to(have_length(1))
    expect(creates[0].parent_case_id).to(equal(_CASE))
    expect(creates[0].tenant_id).to(equal(_TENANT))
    expect([d.document_index for d in creates[0].documents]).to(equal([0, 1, 2]))

    # Refs compactos en scratch para finalize.
    expect(state.scratch["fan_out_children"]).to(have_length(3))
    expect(state.scratch["fan_out_children"][0]["caseId"]).to(
        equal(str(children.children[0].case_id))
    )

    # case_event case.split en el timeline del padre, con dedupe.
    events = [arg for name, arg in calls if name == APPEND_CASE_EVENT_ACTIVITY]
    expect([e.type for e in events]).to(equal([CASE_SPLIT_EVENT]))
    expect(events[0].payload["total"]).to(equal(3))
    expect(events[0].payload["children"]).to(have_length(3))
    expect(events[0].dedupe_key).to(equal(f"run-1:classify:{CASE_SPLIT_EVENT}"))


async def test_classify_pages__without_fan_out_config_calls_no_new_activities(monkeypatch):
    calls: list = []
    _patch(monkeypatch, calls, _classify_responses(2))
    state = _classify_state()
    phase = PhaseSpec(id="classify", kind=PhaseKind.CLASSIFY_PAGES, config={})

    await classify_pages(ProcessingJobWorkflowBase(), phase, state)

    names = [name for name, _ in calls]
    expect(CREATE_CHILD_CASES_ACTIVITY in names).to(equal(False))
    expect(APPEND_CASE_EVENT_ACTIVITY in names).to(equal(False))
    expect("fan_out_children" in state.scratch).to(equal(False))


async def test_classify_pages__fan_out_over_max_children_fails_run(monkeypatch):
    calls: list = []
    _patch(monkeypatch, calls, _classify_responses(3))
    state = _classify_state()
    phase = PhaseSpec(
        id="classify",
        kind=PhaseKind.CLASSIFY_PAGES,
        config={"fan_out": "child_cases", "fan_out_max_children": 2},
    )

    with pytest.raises(ApplicationError) as exc_info:
        await classify_pages(ProcessingJobWorkflowBase(), phase, state)

    expect("fan_out_max_children" in str(exc_info.value)).to(be_true)
    names = [name for name, _ in calls]
    expect(CREATE_CHILD_CASES_ACTIVITY in names).to(equal(False))


async def test_classify_pages__fan_out_types_filters_docs_to_split(monkeypatch):
    # La portada (Circular) queda en el padre; solo las Personas se parten.
    calls: list = []
    mixed = PersistClassifiedDocumentsOutput(
        documents=[
            PersistedDocumentRef(document_id=uuid4(), document_type_name="Circular", document_index=0),
            PersistedDocumentRef(document_id=uuid4(), document_type_name="Persona", document_index=1),
            PersistedDocumentRef(document_id=uuid4(), document_type_name="Persona", document_index=2),
        ]
    )
    children = _children_output(2)
    responses = _classify_responses(3, children)
    from src.workflows.presentation.workflows.base import PERSIST_CLASSIFIED_DOCS_ACTIVITY

    responses[PERSIST_CLASSIFIED_DOCS_ACTIVITY] = mixed
    _patch(monkeypatch, calls, responses)
    state = _classify_state()
    phase = PhaseSpec(
        id="classify",
        kind=PhaseKind.CLASSIFY_PAGES,
        config={"fan_out": "child_cases", "fan_out_types": ["Persona"]},
    )

    await classify_pages(ProcessingJobWorkflowBase(), phase, state)

    creates = [arg for name, arg in calls if name == CREATE_CHILD_CASES_ACTIVITY]
    expect(creates).to(have_length(1))
    expect([d.document_index for d in creates[0].documents]).to(equal([1, 2]))
    expect([d.document_type_name for d in creates[0].documents]).to(equal(["Persona", "Persona"]))


async def test_classify_pages__fan_out_types_without_matches_is_inert(monkeypatch):
    calls: list = []
    _patch(monkeypatch, calls, _classify_responses(2))
    state = _classify_state()
    phase = PhaseSpec(
        id="classify",
        kind=PhaseKind.CLASSIFY_PAGES,
        config={"fan_out": "child_cases", "fan_out_types": ["OtroTipo"]},
    )

    await classify_pages(ProcessingJobWorkflowBase(), phase, state)

    names = [name for name, _ in calls]
    expect(CREATE_CHILD_CASES_ACTIVITY in names).to(equal(False))
    expect(APPEND_CASE_EVENT_ACTIVITY in names).to(equal(False))
    expect("fan_out_children" in state.scratch).to(equal(False))


async def test_classify_pages__fan_out_without_case_id_is_inert(monkeypatch):
    calls: list = []
    _patch(monkeypatch, calls, _classify_responses(2))
    data = _data().model_copy(update={"case_id": None})
    state = PipelineState(data=data, job_id="JOB-1")
    state.extract_text = {"output_uri": "s3://bucket/text.json"}
    phase = PhaseSpec(
        id="classify", kind=PhaseKind.CLASSIFY_PAGES, config={"fan_out": "child_cases"}
    )

    await classify_pages(ProcessingJobWorkflowBase(), phase, state)

    names = [name for name, _ in calls]
    expect(CREATE_CHILD_CASES_ACTIVITY in names).to(equal(False))


# ─── finalize · señales del fan-out ──────────────────────────────────────────


def _finalize_state(children: int) -> PipelineState:
    state = PipelineState(data=_data(), job_id="JOB-1")
    state.extract_text = {"output_uri": "s3://bucket/text.json"}
    state.classify_pages = {"output_uri": "s3://bucket/classify.json"}
    state.extract_fields = {"extractions": [], "errors": []}
    state.validate_extraction = {"validations": [], "errors": []}
    state.persisted_docs = []
    state.completed = []
    state.scratch["run_scope"] = "document"
    if children:
        state.scratch["fan_out_children"] = [
            {"caseId": str(uuid4()), "documentIndex": i, "externalRef": f"CIRC-{i + 1:03d}"}
            for i in range(children)
        ]
    # Sin processing_job: el checkpoint/webhook de finalize hace early-return y
    # el test queda enfocado en las señales.
    state.data.processing_job_uuid = None
    return state


async def test_finalize__fan_out_signals_children_in_batches_and_case_split_to_parent(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {
            START_CHILD_CASE_RUNS_ACTIVITY: StartChildCaseRunsOutput(started=20, signaled=20),
            SIGNAL_CASE_WORKFLOW_ACTIVITY: True,
        },
    )
    state = _finalize_state(children=25)
    phase = PhaseSpec(id="fin", kind=PhaseKind.FINALIZE, config={"dispatch_webhook": False})

    await finalize(ProcessingJobWorkflowBase(), phase, state)

    batches = [arg for name, arg in calls if name == START_CHILD_CASE_RUNS_ACTIVITY]
    expect(batches).to(have_length(2))  # 25 children ⇒ 20 + 5
    expect(batches[0].case_ids).to(have_length(20))
    expect(batches[1].case_ids).to(have_length(5))
    expect(batches[0].tenant_id).to(equal(_TENANT))

    signals = [arg for name, arg in calls if name == SIGNAL_CASE_WORKFLOW_ACTIVITY]
    expect(signals).to(have_length(1))
    expect(signals[0].case_id).to(equal(_CASE))
    expect(signals[0].signal).to(equal(CASE_SPLIT_SIGNAL))


async def test_finalize__without_fan_out_keeps_e4_docs_changed_signal(monkeypatch):
    calls: list = []
    _patch(monkeypatch, calls, {SIGNAL_CASE_WORKFLOW_ACTIVITY: True})
    state = _finalize_state(children=0)
    phase = PhaseSpec(id="fin", kind=PhaseKind.FINALIZE, config={"dispatch_webhook": False})

    await finalize(ProcessingJobWorkflowBase(), phase, state)

    names = [name for name, _ in calls]
    expect(START_CHILD_CASE_RUNS_ACTIVITY in names).to(equal(False))
    signals = [arg for name, arg in calls if name == SIGNAL_CASE_WORKFLOW_ACTIVITY]
    expect(signals).to(have_length(1))
    expect(signals[0].signal).to(equal("case_docs_changed"))


# ─── await_documents · child auto-ready + salida del padre por case_split ────


def _case_state() -> PipelineState:
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
    state.scratch["policies"] = {"activation": None, "completeness": None}
    return state


def _child_completeness() -> EvaluateCaseCompletenessOutput:
    return EvaluateCaseCompletenessOutput(satisfied=False, is_child=True)


async def test_await_documents__child_auto_readies_on_first_docs_changed(monkeypatch):
    calls: list = []
    _patch(
        monkeypatch,
        calls,
        {
            EVALUATE_CASE_COMPLETENESS_ACTIVITY: _child_completeness(),
            MARK_CASE_READY_ACTIVITY: MarkCaseReadyOutput(
                ready_at="2026-06-10T00:00:00+00:00", transitioned=True
            ),
        },
    )
    state = _case_state()
    ctx = ProcessingJobWorkflowBase()
    ctx._case_docs_changed_count = 1  # la señal de finalize ya llegó

    await await_documents(ctx, PhaseSpec(id="await", kind=PhaseKind.AWAIT_DOCUMENTS), state)

    marks = [arg for name, arg in calls if name == MARK_CASE_READY_ACTIVITY]
    expect(marks).to(have_length(1))
    expect(marks[0].auto).to(be_true)
    expect(marks[0].forced).to(equal(False))
    expect(state.artifact("await_documents")["auto"]).to(be_true)


async def test_await_documents__child_waits_until_first_docs_changed(monkeypatch):
    calls: list = []
    ctx = ProcessingJobWorkflowBase()

    def on_wait():
        ctx._case_docs_changed_count += 1

    _patch(
        monkeypatch,
        calls,
        {
            EVALUATE_CASE_COMPLETENESS_ACTIVITY: _child_completeness(),
            MARK_CASE_READY_ACTIVITY: MarkCaseReadyOutput(ready_at="2026-06-10T00:00:00+00:00"),
        },
        on_wait=on_wait,
    )
    state = _case_state()

    await await_documents(ctx, PhaseSpec(id="await", kind=PhaseKind.AWAIT_DOCUMENTS), state)

    evaluates = [arg for name, arg in calls if name == EVALUATE_CASE_COMPLETENESS_ACTIVITY]
    expect(evaluates).to(have_length(2))  # sin docs aún → señal → auto-ready


async def test_await_documents__parent_case_split_exits_processing_and_terminates(monkeypatch):
    calls: list = []
    _patch(monkeypatch, calls, {TRANSITION_CASE_STATUS_ACTIVITY: None})
    state = _case_state()
    ctx = ProcessingJobWorkflowBase()
    ctx._case_split = True  # señal case_split ya recibida

    await await_documents(ctx, PhaseSpec(id="await", kind=PhaseKind.AWAIT_DOCUMENTS), state)

    expect(state.terminated).to(be_true)
    expect(state.scratch["split"]).to(be_true)
    expect(state.artifact("await_documents")).to(equal({"split": True}))
    transitions = [arg for name, arg in calls if name == TRANSITION_CASE_STATUS_ACTIVITY]
    expect([t.to_status for t in transitions]).to(equal(["PROCESSING"]))
    # Jamás evalúa completitud ni marca ready: el padre quedó partido.
    names = [name for name, _ in calls]
    expect(EVALUATE_CASE_COMPLETENESS_ACTIVITY in names).to(equal(False))
    expect(MARK_CASE_READY_ACTIVITY in names).to(equal(False))


async def test_await_documents__case_split_mid_wait_exits_loop(monkeypatch):
    calls: list = []
    ctx = ProcessingJobWorkflowBase()

    def on_wait():
        ctx._case_split = True

    _patch(
        monkeypatch,
        calls,
        {
            EVALUATE_CASE_COMPLETENESS_ACTIVITY: EvaluateCaseCompletenessOutput(satisfied=False),
            TRANSITION_CASE_STATUS_ACTIVITY: None,
        },
        on_wait=on_wait,
    )
    state = _case_state()

    await await_documents(ctx, PhaseSpec(id="await", kind=PhaseKind.AWAIT_DOCUMENTS), state)

    expect(state.terminated).to(be_true)
    evaluates = [arg for name, arg in calls if name == EVALUATE_CASE_COMPLETENESS_ACTIVITY]
    expect(evaluates).to(have_length(1))  # evaluó, esperó, y el split lo sacó


# ─── validate_phases · config fan_out ────────────────────────────────────────


def _phase(kind: str, config: dict | None = None, id_: str = "p1") -> PhaseSpec:
    return PhaseSpec(id=id_, kind=PhaseKind(kind), config=config or {})


def test_validate_phases__fan_out_on_classify_pages_is_valid():
    validate_phases(
        [_phase("classify_pages", {"fan_out": "child_cases", "fan_out_max_children": 100})]
    )


def test_validate_phases__fan_out_outside_classify_pages_rejected():
    with pytest.raises(InvalidPipelinePhasesError):
        validate_phases([_phase("extract_fields", {"fan_out": "child_cases"})])


def test_validate_phases__fan_out_invalid_mode_rejected():
    with pytest.raises(InvalidPipelinePhasesError):
        validate_phases([_phase("classify_pages", {"fan_out": "inline"})])


def test_validate_phases__fan_out_max_children_must_be_positive_int():
    for bad in (0, -1, "500", True, 1.5):
        with pytest.raises(InvalidPipelinePhasesError):
            validate_phases([_phase("classify_pages", {"fan_out": "child_cases", "fan_out_max_children": bad})])


def test_validate_phases__max_children_without_fan_out_still_requires_classify():
    with pytest.raises(InvalidPipelinePhasesError):
        validate_phases([_phase("finalize", {"fan_out_max_children": 10})])


def test_validate_phases__fan_out_types_valid_list_accepted():
    validate_phases(
        [_phase("classify_pages", {"fan_out": "child_cases", "fan_out_types": ["persona_embargo"]})]
    )


def test_validate_phases__fan_out_types_invalid_shapes_rejected():
    for bad in ([], "persona", [1], [""], ["ok", 2]):
        with pytest.raises(InvalidPipelinePhasesError):
            validate_phases(
                [_phase("classify_pages", {"fan_out": "child_cases", "fan_out_types": bad})]
            )


def test_validate_phases__fan_out_types_without_fan_out_rejected():
    with pytest.raises(InvalidPipelinePhasesError):
        validate_phases([_phase("classify_pages", {"fan_out_types": ["persona_embargo"]})])
