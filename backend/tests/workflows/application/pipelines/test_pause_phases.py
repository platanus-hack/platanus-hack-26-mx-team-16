"""F6: durable pause phases open a HumanTask and resume on resolution."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from expects import equal, expect
from temporalio import workflow as tw

from src.common.domain.entities.workflows.document_processing import DocumentProcessingInput
from src.common.domain.entities.workflows.human_task_io import CreateHumanTaskOutput
from src.common.domain.enums.pipelines import PhaseKind
from src.workflows.application.pipelines import pause_phases as pp
from src.workflows.application.pipelines.pause_phases import CREATE_HUMAN_TASK_ACTIVITY
from src.workflows.application.pipelines.runtime import PipelineState
from src.workflows.domain.models.pipeline import PhaseSpec
from src.workflows.presentation.workflows.base import ProcessingJobWorkflowBase

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_FIXED_DT = datetime(2026, 6, 9, 12, 0, 0, tzinfo=UTC)


def _patch(monkeypatch, calls: list) -> None:
    async def fake_execute_activity(name, arg=None, **kwargs):
        calls.append((name, arg))
        if name == CREATE_HUMAN_TASK_ACTIVITY:
            return CreateHumanTaskOutput(task_id=uuid4(), task_key=arg.task_key)
        return None

    async def fake_wait_condition(predicate, *a, **k):
        return None  # condition already satisfied (resolution pre-seeded)

    monkeypatch.setattr(tw, "execute_activity", fake_execute_activity)
    monkeypatch.setattr(tw, "wait_condition", fake_wait_condition)
    monkeypatch.setattr(tw, "now", lambda: _FIXED_DT)
    monkeypatch.setattr(tw, "info", lambda: SimpleNamespace(workflow_id="run-1", run_id="r1"))
    monkeypatch.setattr(tw, "logger", SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None))


async def test_human_review__opens_task_and_resumes_on_resolution(monkeypatch):
    calls: list = []
    _patch(monkeypatch, calls)

    ctx = ProcessingJobWorkflowBase()
    ctx._resolved_tasks["run-1:review1"] = {"approved": True}  # the signal already arrived

    data = DocumentProcessingInput(object_key="s3://b/x", document_types=[], job_id="J", tenant_id=_TENANT)
    state = PipelineState(data=data, job_id="J")
    phase = PhaseSpec(id="review1", kind=PhaseKind.HUMAN_REVIEW, config={"audience": "bank_analyst"})

    await pp.human_review(ctx, phase, state)

    created = [arg for name, arg in calls if name == CREATE_HUMAN_TASK_ACTIVITY]
    expect(len(created)).to(equal(1))
    expect(created[0].task_key).to(equal("run-1:review1"))
    expect(created[0].audience).to(equal("bank_analyst"))
    expect(state.scratch["resolutions"]["review1"]).to(equal({"approved": True}))


async def test_await_clarification__noop_without_tenant(monkeypatch):
    calls: list = []
    _patch(monkeypatch, calls)

    data = DocumentProcessingInput(object_key="s3://b/x", document_types=[], job_id="J")  # no tenant
    state = PipelineState(data=data, job_id="J")
    phase = PhaseSpec(id="clar1", kind=PhaseKind.AWAIT_CLARIFICATION)

    await pp.await_clarification(ProcessingJobWorkflowBase(), phase, state)

    expect(calls).to(equal([]))
