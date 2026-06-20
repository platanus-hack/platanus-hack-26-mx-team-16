"""E4 · diseño §3: ``finalize`` señala al CASE# solo desde runs document-scope.

Un run document-scope con ``case_id`` debe emitir ``signal_case_workflow``
(best-effort) tras el webhook de finalize, para que ``await_documents``
re-evalúe la completitud. Un run full (receta sin ``await_documents`` — golden,
standard-analysis) NO debe emitirla: no hay workflow de caso esperando.
"""

from __future__ import annotations

from expects import contain, equal, expect

from src.workflows.application.pipelines import (  # noqa: F401 — side effects: pueblan PHASE_LIBRARY
    extraction_phases,
)
from src.workflows.application.pipelines.runtime import PipelineState, execute_pipeline
from src.workflows.domain.models.pipeline import PhaseSpec
from src.workflows.domain.recipes import standard_extraction_phases
from src.workflows.presentation.workflows.activities.case_runtime_activities import (
    SIGNAL_CASE_WORKFLOW_ACTIVITY,
)
from src.workflows.presentation.workflows.base import (
    DISPATCH_PROCESSING_JOB_WEBHOOK_ACTIVITY,
    ProcessingJobWorkflowBase,
)
from tests.workflows.application.pipelines.test_standard_v1_regression import (
    _JOB_ID,
    _golden_input,
    _load_golden,
    _make_canned,
    _patch_workflow_runtime,
)


def _canned_with_signal(base):
    def _canned(name, arg):
        if name == SIGNAL_CASE_WORKFLOW_ACTIVITY:
            return True
        return base(name, arg)

    return _canned


async def _replay_standard(monkeypatch, run_scope: str | None) -> list:
    canned, _, _ = _load_golden()
    calls: list = []
    _patch_workflow_runtime(monkeypatch, calls, _canned_with_signal(_make_canned(canned)))

    phases = [PhaseSpec.model_validate(p) for p in standard_extraction_phases()]
    state = PipelineState(data=_golden_input(), job_id=_JOB_ID)
    state.scratch["run_scope"] = run_scope
    await execute_pipeline(ProcessingJobWorkflowBase(), phases, state)
    return calls


async def test_finalize__document_scope_signals_case_after_webhook(monkeypatch):
    # Act — el golden input lleva case_id; en scope "document" sí hay CASE#.
    calls = await _replay_standard(monkeypatch, run_scope="document")

    # Assert — la señal existe y va DESPUÉS del webhook terminal de finalize.
    names = [c[0] for c in calls]
    expect(names).to(contain(SIGNAL_CASE_WORKFLOW_ACTIVITY))
    expect(names.index(SIGNAL_CASE_WORKFLOW_ACTIVITY) > names.index(DISPATCH_PROCESSING_JOB_WEBHOOK_ACTIVITY)).to(
        equal(True)
    )


async def test_finalize__full_scope_run_does_not_signal(monkeypatch):
    # Act — mismo input con case_id, pero run full (paridad golden E1).
    calls = await _replay_standard(monkeypatch, run_scope=None)

    # Assert
    names = [c[0] for c in calls]
    expect(SIGNAL_CASE_WORKFLOW_ACTIVITY in names).to(equal(False))
