"""E7 · F1 (caso universal · straight-through): finalize cierra el caso.

Una receta de pura extracción (``standard_extraction_phases``, sin fases
case-scope) que corre full (scope=None) sobre un caso no tendría quién lo cierre
— ni ``analyze`` (PROCESSING) ni ``deliver`` (COMPLETED) existen. El intérprete
siembra ``finalize_closes_case`` y ``finalize`` cierra el caso
RECEIVING→PROCESSING→COMPLETED. Sin esa instrucción (tests de fase, golden) es un
no-op: la paridad de extracción no se mueve.

Reusa el harness del golden E1 (``test_standard_v1_regression``).
"""

from __future__ import annotations

from types import SimpleNamespace

from expects import be_empty, equal, expect
from temporalio import workflow as tw

from src.common.domain.enums.workflow_cases import WorkflowCaseStatus
from src.workflows.application.pipelines.case_transitions import (
    TRANSITION_CASE_STATUS_ACTIVITY,
)
from src.workflows.application.pipelines.runtime import PipelineState, execute_pipeline
from src.workflows.presentation.workflows.base import ProcessingJobWorkflowBase
from tests.workflows.application.pipelines.test_standard_v1_regression import (
    _FIXED_DT,
    _JOB_ID,
    _golden_input,
    _load_golden,
    _make_canned,
    _standard_phases,
)


async def _replay(monkeypatch, *, finalize_closes_case: bool | None) -> list[str]:
    """Corre la receta de extracción y devuelve los ``to_status`` de las
    transiciones de caso que emitió el run."""
    canned, _, _ = _load_golden()
    transitions: list[str] = []
    base_canned = _make_canned(canned)

    async def fake_execute_activity(name, arg=None, **kwargs):
        if name == TRANSITION_CASE_STATUS_ACTIVITY:
            transitions.append(arg.to_status)
            return None
        return base_canned(name, arg)

    async def fake_wait_condition(*args, **kwargs):
        return None

    monkeypatch.setattr(tw, "execute_activity", fake_execute_activity)
    monkeypatch.setattr(tw, "wait_condition", fake_wait_condition)
    monkeypatch.setattr(tw, "now", lambda: _FIXED_DT)
    monkeypatch.setattr(tw, "info", lambda: SimpleNamespace(run_id="run-1"))
    monkeypatch.setattr(
        tw, "logger", SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None)
    )

    state = PipelineState(data=_golden_input(), job_id=_JOB_ID)
    if finalize_closes_case is not None:
        state.scratch["finalize_closes_case"] = finalize_closes_case
    await execute_pipeline(ProcessingJobWorkflowBase(), _standard_phases(), state)
    return transitions


async def test_finalize_closes_straight_through_case(monkeypatch):
    # El intérprete sembró la instrucción ⇒ finalize cierra el caso.
    transitions = await _replay(monkeypatch, finalize_closes_case=True)

    expect(transitions).to(
        equal([WorkflowCaseStatus.PROCESSING.value, WorkflowCaseStatus.COMPLETED.value])
    )


async def test_finalize_does_not_touch_case_without_instruction(monkeypatch):
    # Sin la instrucción (golden / tests de fase / runs con cola case-scope) el
    # finalize NO toca el estado del caso — la paridad de extracción no se mueve.
    transitions = await _replay(monkeypatch, finalize_closes_case=None)

    expect(transitions).to(be_empty)
