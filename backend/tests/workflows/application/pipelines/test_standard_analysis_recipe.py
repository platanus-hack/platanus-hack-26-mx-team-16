"""Receta encadenada ``standard-analysis@v1`` (E2): extracción + caso end-to-end.

Extiende el harness del golden E1 (``test_standard_v1_regression``): mismos
canned results para la familia de extracción, más stubs para las activities
case-scope y el child workflow de análisis. Verifica que:

- la receta REAL ``standard_analysis_phases()`` pasa ``validate_phases`` contra
  el ``PHASE_LIBRARY`` poblado (todos los kinds tienen handler tras E2),
- un run end-to-end ejecuta las 9 fases en orden: la secuencia de extracción
  es EXACTAMENTE la del golden (la cola analyze→output→deliver no perturba la
  paridad E1) seguida de create_analysis_run → child → build_case_output →
  dispatch_case_event.
"""

from __future__ import annotations

from uuid import UUID

from expects import equal, expect, have_length
from temporalio import workflow as tw
from temporalio.workflow import ParentClosePolicy

from src.common.domain.entities.workflows.analysis_run_processing import (
    BuildCaseOutputOutput,
    CreateAnalysisRunForPipelineOutput,
)
from src.common.domain.enums.pipelines import PhaseKind
from src.workflows.application.pipelines import (  # noqa: F401 — side effects: pueblan PHASE_LIBRARY
    analysis_phases,
    extraction_phases,
)
from src.workflows.application.pipelines.analysis_phases import (
    ANALYSIS_CHILD_WORKFLOW,
    BUILD_CASE_OUTPUT_ACTIVITY,
    CREATE_ANALYSIS_RUN_ACTIVITY,
    DISPATCH_CASE_EVENT_ACTIVITY,
)
from src.workflows.application.pipelines.case_transitions import (
    TRANSITION_CASE_STATUS_ACTIVITY,
)
from src.workflows.application.pipelines.runtime import (
    PHASE_LIBRARY,
    PipelineState,
    execute_pipeline,
)
from src.workflows.domain.models.pipeline import PhaseSpec
from src.workflows.domain.recipes import standard_analysis_phases
from src.workflows.domain.services.pipeline_validation import validate_phases
from src.workflows.presentation.workflows.base import ProcessingJobWorkflowBase
from tests.workflows.application.pipelines.test_standard_v1_regression import (
    _JOB_ID,
    _golden_input,
    _load_golden,
    _make_canned,
    _patch_workflow_runtime,
)

_RUN_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")

_CASE_TAIL_KINDS = (PhaseKind.ANALYZE.value, PhaseKind.OUTPUT.value, PhaseKind.DELIVER.value)


def _analysis_phase_specs() -> list[PhaseSpec]:
    """La receta REAL que siembran el onboarder y la migración E2 — no una copia."""
    return [PhaseSpec.model_validate(p) for p in standard_analysis_phases()]


def _canned_with_case_tail(base):
    """Canned results del golden + stubs de las activities case-scope (E2)."""

    def _canned(name, arg):
        if name == CREATE_ANALYSIS_RUN_ACTIVITY:
            return CreateAnalysisRunForPipelineOutput(run_id=arg.run_id, created=True)
        if name == BUILD_CASE_OUTPUT_ACTIVITY:
            return BuildCaseOutputOutput(
                run_id=arg.run_id,
                verdict="APPROVED",
                narrative_status="COMPLETED",
                has_output=True,
                document_outputs=2,
            )
        if name == DISPATCH_CASE_EVENT_ACTIVITY:
            return 1
        return base(name, arg)

    return _canned


async def _replay_standard_analysis(monkeypatch) -> tuple[list, list, PipelineState]:
    canned, _, _ = _load_golden()
    calls: list = []
    children: list = []
    _patch_workflow_runtime(monkeypatch, calls, _canned_with_case_tail(_make_canned(canned)))

    async def fake_execute_child_workflow(name, arg=None, **kwargs):
        children.append((name, arg, kwargs))
        return None

    monkeypatch.setattr(tw, "execute_child_workflow", fake_execute_child_workflow)
    monkeypatch.setattr(tw, "uuid4", lambda: _RUN_ID)

    # Mismo job_id que el golden: el output final del set debe ser idéntico
    # campo a campo aunque la receta encadene la cola analyze→output→deliver.
    state = PipelineState(data=_golden_input(), job_id=_JOB_ID)
    state = await execute_pipeline(ProcessingJobWorkflowBase(), _analysis_phase_specs(), state)
    return calls, children, state


# ─── La receta valida contra el PHASE_LIBRARY real ──────────────────────────


def test_standard_analysis_recipe__passes_validate_phases_against_phase_library():
    validate_phases(_analysis_phase_specs(), known_kinds=set(PHASE_LIBRARY))  # no raise


def test_standard_analysis_recipe__is_extraction_recipe_plus_case_tail():
    kinds = [phase["kind"] for phase in standard_analysis_phases()]

    expect(kinds).to(have_length(9))
    expect(tuple(kinds[-3:])).to(equal(_CASE_TAIL_KINDS))


# ─── Run end-to-end: 9 fases en orden con canned activities ─────────────────


async def test_standard_analysis__extraction_sequence_keeps_golden_parity(monkeypatch):
    # Arrange
    _, golden_sequence, _ = _load_golden()

    # Act
    calls, _, _ = await _replay_standard_analysis(monkeypatch)

    # Assert — la cola case-scope NO perturba la orquestación de extracción E1
    extraction_calls = calls[: len(golden_sequence)]
    for index, (got, expected) in enumerate(zip(extraction_calls, golden_sequence)):
        expect((index, got)).to(equal((index, expected)))


async def test_standard_analysis__case_tail_runs_in_order_after_finalize(monkeypatch):
    # Arrange
    _, golden_sequence, _ = _load_golden()

    # Act
    calls, children, state = await _replay_standard_analysis(monkeypatch)

    # Assert — tras el golden: transiciones E4 (PROCESSING→ANALYZING) →
    # create_analysis_run → build_case_output → dispatch → COMPLETED
    tail = calls[len(golden_sequence) :]
    expect(tail).to(
        equal(
            [
                [TRANSITION_CASE_STATUS_ACTIVITY],
                [TRANSITION_CASE_STATUS_ACTIVITY],
                [CREATE_ANALYSIS_RUN_ACTIVITY],
                [BUILD_CASE_OUTPUT_ACTIVITY],
                [DISPATCH_CASE_EVENT_ACTIVITY],
                [TRANSITION_CASE_STATUS_ACTIVITY],
            ]
        )
    )

    # Assert — el child de análisis corre entre la creación y el output
    expect(children).to(have_length(1))
    child_name, child_arg, child_kwargs = children[0]
    expect(child_name).to(equal(ANALYSIS_CHILD_WORKFLOW))
    expect(child_arg.run_id).to(equal(_RUN_ID))
    expect(child_kwargs["parent_close_policy"]).to(equal(ParentClosePolicy.ABANDON))

    # Assert — artifacts de la cola case-scope encadenados por run_id (el artifact
    # analyze también sella providers/rule_set para el re-analyze; H1/H2).
    expect(state.artifact("analysis_run")["run_id"]).to(equal(str(_RUN_ID)))
    expect(state.artifact("case_output")["run_id"]).to(equal(str(_RUN_ID)))
    expect(state.artifact("delivery")).to(equal({"event": "case.output.ready", "dispatched": 1}))


async def test_standard_analysis__final_output_matches_golden_state(monkeypatch):
    # Arrange — el output del set (E1) no cambia por encadenar el caso
    _, _, golden_state = _load_golden()

    # Act
    _, _, state = await _replay_standard_analysis(monkeypatch)

    # Assert
    dumped = state.output.model_dump(mode="json")
    for field, expected in golden_state.items():
        expect((field, dumped[field])).to(equal((field, expected)))
