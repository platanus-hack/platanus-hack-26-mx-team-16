"""F3 · W1: analysis_run.completed emission.

Drives ``WorkflowSummaryWebhookDispatcher`` with fake repos (the dispatcher news
up SQL repos from a session_maker, so we patch those classes) to assert it:
fans out one signed delivery per subscribed destination, carries the
output_schema-shaped payload (W1), and is a no-op until the narrative is ready.
"""

from types import SimpleNamespace
from uuid import UUID, uuid4

from expects import equal, expect

import src.workflows.infrastructure.services.webhooks.summary_dispatcher as mod
from src.common.domain.enums.run_summary import NarrativeStatus, Verdict
from src.common.domain.enums.webhooks import WebhookEventType
from src.common.domain.models.processing.workflow_analysis_run_summary import (
    WorkflowAnalysisRunSummary,
)
from src.workflows.infrastructure.services.webhooks.summary_dispatcher import (
    WorkflowSummaryWebhookDispatcher,
    build_analysis_run_payload,
)

_RUN_ID = UUID("11111111-1111-1111-1111-111111111111")
_TENANT_ID = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW_ID = UUID("33333333-3333-3333-3333-333333333333")


def _summary(narrative_status: NarrativeStatus = NarrativeStatus.COMPLETED) -> WorkflowAnalysisRunSummary:
    return WorkflowAnalysisRunSummary(
        workflow_analysis_run_id=_RUN_ID,
        tenant_id=_TENANT_ID,
        verdict=Verdict.REVIEW,
        output={"people": ["A", "B"]},
        output_schema_snapshot={"type": "object"},
        narrative_status=narrative_status,
        input_hash="hash-1",
    )


class _FakeSessionCM:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *exc):
        return False


class _FakeEventRepo:
    def __init__(self):
        self.created = []
        self.updates = 0

    async def find_by_unique_destination(self, *args):
        return None

    async def create(self, event):
        self.created.append(event)
        return event

    async def update(self, event):
        self.updates += 1
        return event


class _FakeDeliverer:
    def __init__(self):
        self.calls = 0

    async def deliver(self, **kwargs):
        self.calls += 1
        return SimpleNamespace(delivered=True, attempts=1, status_code=200, error=None)


def _patch(monkeypatch, *, destinations, event_repo):
    monkeypatch.setattr(
        mod,
        "SQLWorkflowAnalysisRunRepository",
        lambda session: SimpleNamespace(find_by_id=_async_returning(SimpleNamespace(workflow_id=_WORKFLOW_ID))),
    )
    monkeypatch.setattr(
        mod,
        "SQLWebhookDestinationRepository",
        lambda session: SimpleNamespace(list_enabled_for_event=_async_returning(destinations)),
    )
    monkeypatch.setattr(mod, "SQLWorkflowEventRepository", lambda session: event_repo)


def _async_returning(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner


def test_build_analysis_run_payload__is_output_schema_shaped():
    payload = build_analysis_run_payload(
        event_id="evt_x", run_id=_RUN_ID, workflow_id=_WORKFLOW_ID, summary=_summary()
    )

    expect(payload["eventType"]).to(equal(WebhookEventType.ANALYSIS_RUN_COMPLETED.value))
    expect(payload["data"]["output"]).to(equal({"people": ["A", "B"]}))
    expect(payload["data"]["outputSchema"]).to(equal({"type": "object"}))


async def test_dispatch__fans_out_to_subscribed_destination(monkeypatch):
    destination = SimpleNamespace(uuid=uuid4(), url="https://hook.example/x", secret="whsec_abc")
    event_repo = _FakeEventRepo()
    deliverer = _FakeDeliverer()
    _patch(monkeypatch, destinations=[destination], event_repo=event_repo)

    dispatcher = WorkflowSummaryWebhookDispatcher(session_maker=_FakeSessionCM, dispatcher=deliverer)
    await dispatcher.dispatch(run_id=_RUN_ID, summary=_summary())

    expect(len(event_repo.created)).to(equal(1))
    expect(event_repo.created[0].event_type).to(equal(WebhookEventType.ANALYSIS_RUN_COMPLETED))
    expect(deliverer.calls).to(equal(1))


async def test_dispatch__noop_until_narrative_completed(monkeypatch):
    event_repo = _FakeEventRepo()
    deliverer = _FakeDeliverer()
    _patch(monkeypatch, destinations=[SimpleNamespace(uuid=uuid4(), url="u", secret="s")], event_repo=event_repo)

    dispatcher = WorkflowSummaryWebhookDispatcher(session_maker=_FakeSessionCM, dispatcher=deliverer)
    await dispatcher.dispatch(run_id=_RUN_ID, summary=_summary(NarrativeStatus.PENDING))

    expect(len(event_repo.created)).to(equal(0))
    expect(deliverer.calls).to(equal(0))
