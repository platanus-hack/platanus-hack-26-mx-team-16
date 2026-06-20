"""E2 split: SYSTEM-triggered runs skip synthesis + webhook in complete_run.

The pipeline interpreter's `output` phase runs SynthesisRunner and its
`deliver` phase emits the webhooks — `CompleteWorkflowAnalysisRun` must only
produce the deterministic verdict layer for those runs.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec
from uuid import uuid4

from expects import be_false, be_true, equal, expect

import src.workflows.application.analysis_run_summary.complete_run as complete_run_module
import src.workflows.application.analysis_run_summary.regenerate_on_run_complete as regen_module
from src.common.domain.enums.run_summary import NarrativeStatus
from src.common.domain.enums.workflow_rules import (
    WorkflowAnalysisRunStatus,
    WorkflowAnalysisRunTrigger,
)
from src.common.domain.models.processing.workflow_analysis_run import WorkflowAnalysisRun
from src.common.domain.models.processing.workflow_analysis_run_summary import (
    WorkflowAnalysisRunSummary,
)
from src.common.infrastructure.event_publisher import EventPublisher
from src.workflows.application.analysis_run_summary.complete_run import (
    CompleteWorkflowAnalysisRun,
)
from src.workflows.application.analysis_run_summary.regenerate_on_run_complete import (
    WorkflowAnalysisRunSummarizer,
)
from src.workflows.domain.repositories.workflow_analysis_run import (
    WorkflowAnalysisRunRepository,
)

TENANT_ID = uuid4()
RUN_ID = uuid4()


def _run(trigger: WorkflowAnalysisRunTrigger) -> WorkflowAnalysisRun:
    return WorkflowAnalysisRun(
        uuid=RUN_ID,
        tenant_id=TENANT_ID,
        workflow_id=uuid4(),
        workflow_case_id=uuid4(),
        status=WorkflowAnalysisRunStatus.COMPLETED,
        trigger=trigger,
    )


def _summary(narrative_status=NarrativeStatus.PENDING) -> WorkflowAnalysisRunSummary:
    return WorkflowAnalysisRunSummary(
        workflow_analysis_run_id=RUN_ID,
        tenant_id=TENANT_ID,
        narrative_status=narrative_status,
        input_hash="h",
    )


async def _execute_complete_run(monkeypatch, *, trigger, captured):
    run_repository = create_autospec(
        spec=WorkflowAnalysisRunRepository, spec_set=True, instance=True
    )
    run_repository.find_by_id.return_value = _run(trigger)

    class _FakeSummarizer:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def execute(self):
            return _summary()

    monkeypatch.setattr(complete_run_module, "WorkflowAnalysisRunSummarizer", _FakeSummarizer)
    dispatcher = SimpleNamespace(dispatch=AsyncMock())

    use_case = CompleteWorkflowAnalysisRun(
        tenant=None,
        run_id=RUN_ID,
        tenant_id=TENANT_ID,
        workflow_repository=MagicMock(),
        run_repository=run_repository,
        rule_repository=MagicMock(),
        result_repository=MagicMock(),
        summary_repository=MagicMock(),
        agent=MagicMock(),
        event_publisher=MagicMock(),
        webhook_dispatcher=dispatcher,
    )
    await use_case.execute()
    return dispatcher


async def test_execute__system_trigger_skips_synthesis_and_webhook(monkeypatch):
    captured: dict = {}

    dispatcher = await _execute_complete_run(
        monkeypatch, trigger=WorkflowAnalysisRunTrigger.SYSTEM, captured=captured
    )

    expect(captured["synthesize"]).to(be_false)
    dispatcher.dispatch.assert_not_awaited()


async def test_execute__user_trigger_keeps_synthesis_and_webhook(monkeypatch):
    captured: dict = {}

    dispatcher = await _execute_complete_run(
        monkeypatch, trigger=WorkflowAnalysisRunTrigger.USER, captured=captured
    )

    expect(captured["synthesize"]).to(be_true)
    dispatcher.dispatch.assert_awaited_once()


async def test_summarizer__synthesize_false_leaves_narrative_pending(monkeypatch):
    pending = _summary(NarrativeStatus.PENDING)

    class _FakeAggregator:
        def __init__(self, **kwargs):
            pass

        async def execute(self):
            return pending

    synthesis_ctor = MagicMock()
    monkeypatch.setattr(regen_module, "VerdictAggregator", _FakeAggregator)
    monkeypatch.setattr(regen_module, "SynthesisRunner", synthesis_ctor)
    event_publisher = create_autospec(spec=EventPublisher, instance=True)

    summary = await WorkflowAnalysisRunSummarizer(
        run_id=RUN_ID,
        tenant_id=TENANT_ID,
        workflow_repository=MagicMock(),
        run_repository=MagicMock(),
        rule_repository=MagicMock(),
        result_repository=MagicMock(),
        summary_repository=MagicMock(),
        agent=MagicMock(),
        event_publisher=event_publisher,
        synthesize=False,
    ).execute()

    expect(summary.narrative_status).to(equal(NarrativeStatus.PENDING))
    synthesis_ctor.assert_not_called()
    # Only the verdict_ready event was published — no narrative_started.
    expect(event_publisher.publish.await_count).to(equal(1))
