"""F5/E3: enrich phase — virtual doc plumbing, on_failure modes."""

import logging
from types import SimpleNamespace
from uuid import UUID, uuid4

from expects import contain, equal, expect
from temporalio import workflow as tw
from temporalio.exceptions import ActivityError, ApplicationError

from src.common.domain.entities.workflows.document_processing import DocumentProcessingInput
from src.common.domain.entities.workflows.tool_lookup import (
    ENRICH_CONFIG_ERROR_TYPE,
    ToolLookupOutput,
)
from src.common.domain.enums.tools import ToolCallStatus
from src.workflows.application.pipelines import enrich_phases as ep
from src.workflows.application.pipelines.runtime import PipelineState

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")
_CASE = UUID("44444444-4444-4444-4444-444444444444")


def _state(*, with_case: bool = False) -> PipelineState:
    data = DocumentProcessingInput(
        object_key="s3://b/in.pdf",
        document_types=[],
        job_id="JOB-1",
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW if with_case else None,
        case_id=_CASE if with_case else None,
    )
    return PipelineState(data=data, job_id="JOB-1")


def _ctx(checkpoints: list | None = None) -> SimpleNamespace:
    checkpoints = checkpoints if checkpoints is not None else []

    async def _checkpoint(data, **kwargs):
        checkpoints.append(kwargs)

    return SimpleNamespace(_checkpoint=_checkpoint, checkpoints=checkpoints)


def _phase(**config) -> SimpleNamespace:
    return SimpleNamespace(id="e1", config={"tool": "lookup_poliza", **config})


def _router(monkeypatch, responses: dict, calls: list):
    """Route fake execute_activity by activity name; record (name, arg, kwargs)."""

    async def fake_execute_activity(name, arg=None, **kwargs):
        calls.append((name, arg, kwargs))
        result = responses[name]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(tw, "execute_activity", fake_execute_activity)
    monkeypatch.setattr(tw, "info", lambda: SimpleNamespace(workflow_id="wf-run-1"), raising=False)
    # tw.logger requires a live workflow event loop — stub it out for unit tests.
    monkeypatch.setattr(tw, "logger", logging.getLogger("test.enrich"), raising=False)


def _activity_error(cause: Exception) -> ActivityError:
    err = ActivityError(
        "activity failed",
        scheduled_event_id=1,
        started_event_id=1,
        identity="worker",
        activity_type="tool_lookup",
        activity_id="1",
        retry_state=None,
    )
    err.__cause__ = cause
    return err


# ── happy path ──────────────────────────────────────────────────────────────


async def test_enrich__ok_writes_scratch_with_document_id_and_checkpoints(monkeypatch):
    doc_id = uuid4()
    calls: list = []
    _router(
        monkeypatch,
        {"tool_lookup": ToolLookupOutput(status=ToolCallStatus.OK, data={"saldo": 10}, document_id=doc_id)},
        calls,
    )
    ctx, state = _ctx(), _state(with_case=True)

    await ep.enrich(ctx, _phase(output_key="poliza", args={"q": "x"}), state)

    expect(state.scratch["enrichment"]["poliza"]).to(
        equal({"status": "OK", "data": {"saldo": 10}, "error": None, "document_id": str(doc_id)})
    )
    expect(len(ctx.checkpoints)).to(equal(1))
    expect(ctx.checkpoints[0]["payload"]["step"]).to(equal("enrich"))
    expect(ctx.checkpoints[0]["payload"]["status"]).to(equal("OK"))
    # Only the tool_lookup activity ran (no human task, no case.failed).
    expect([name for name, *_ in calls]).to(equal(["tool_lookup"]))


async def test_enrich__unifies_retries_single_activity_attempt_60s(monkeypatch):
    calls: list = []
    _router(monkeypatch, {"tool_lookup": ToolLookupOutput(status=ToolCallStatus.OK, data={})}, calls)

    await ep.enrich(_ctx(), _phase(), _state(with_case=True))

    name, arg, kwargs = calls[0]
    expect(name).to(equal("tool_lookup"))
    expect(kwargs["retry_policy"].maximum_attempts).to(equal(1))
    expect(kwargs["start_to_close_timeout"].total_seconds()).to(equal(60.0))
    expect(arg.workflow_id).to(equal(_WORKFLOW))
    expect(arg.case_id).to(equal(_CASE))


async def test_enrich__noop_without_tool_name(monkeypatch):
    async def boom(*a, **k):
        raise AssertionError("should not call the activity")

    monkeypatch.setattr(tw, "execute_activity", boom)
    state = _state()

    await ep.enrich(_ctx(), SimpleNamespace(id="e1", config={}), state)

    expect("enrichment" in state.scratch).to(equal(False))


# ── on_failure: review (default) ────────────────────────────────────────────


async def test_enrich__degraded_default_review_opens_task_and_continues(monkeypatch):
    calls: list = []
    _router(
        monkeypatch,
        {
            "tool_lookup": ToolLookupOutput(status=ToolCallStatus.DEGRADED, error="http_500"),
            "create_human_task": SimpleNamespace(task_id=uuid4(), task_key="k"),
        },
        calls,
    )
    ctx, state = _ctx(), _state(with_case=True)

    await ep.enrich(ctx, _phase(), state)  # no raise → run continues

    names = [name for name, *_ in calls]
    expect(names).to(equal(["tool_lookup", "create_human_task"]))
    task_input = calls[1][1]
    expect(task_input.kind.value).to(equal("approval"))
    expect(task_input.assignee_mode.value).to(equal("internal_queue"))
    expect(task_input.payload).to(equal({"tool": "lookup_poliza", "error": "http_500", "case_id": str(_CASE)}))
    expect(task_input.task_key).to(equal("wf-run-1:e1:enrich_review"))
    expect(state.scratch["enrichment"]["lookup_poliza"]["degraded"]).to(equal(True))
    expect(state.scratch["enrichment_reviews"]["e1"]["task_key"]).to(equal("wf-run-1:e1:enrich_review"))
    expect(ctx.checkpoints[0]["payload"]["on_failure"]).to(equal("review"))


# ── on_failure: continue ────────────────────────────────────────────────────


async def test_enrich__degraded_continue_marks_scratch_and_moves_on(monkeypatch):
    calls: list = []
    _router(
        monkeypatch,
        {"tool_lookup": ToolLookupOutput(status=ToolCallStatus.DEGRADED, error="circuit_open")},
        calls,
    )
    ctx, state = _ctx(), _state(with_case=True)

    await ep.enrich(ctx, _phase(on_failure="continue"), state)

    expect([name for name, *_ in calls]).to(equal(["tool_lookup"]))  # no task, no dispatch
    expect(state.scratch["enrichment"]["lookup_poliza"]["degraded"]).to(equal(True))
    expect(ctx.checkpoints[0]["payload"]["on_failure"]).to(equal("continue"))


# ── on_failure: fail ────────────────────────────────────────────────────────


async def test_enrich__degraded_fail_dispatches_case_failed_then_raises(monkeypatch):
    calls: list = []
    _router(
        monkeypatch,
        {
            "tool_lookup": ToolLookupOutput(status=ToolCallStatus.DEGRADED, error="http_500"),
            "dispatch_case_event": True,
        },
        calls,
    )

    try:
        await ep.enrich(_ctx(), _phase(on_failure="fail"), _state(with_case=True))
        raise AssertionError("expected ApplicationError")
    except ApplicationError as exc:
        expect(exc.type).to(equal("pipeline.enrich_failed"))

    names = [name for name, *_ in calls]
    expect(names).to(equal(["tool_lookup", "dispatch_case_event"]))
    event_input = calls[1][1]
    expect(event_input.event_type).to(equal("case.failed"))
    expect(event_input.error["code"]).to(equal("pipeline.enrich_failed"))


# ── config errors (never on_failure) ────────────────────────────────────────


async def test_enrich__invalid_on_failure_value_is_config_error(monkeypatch):
    async def boom(*a, **k):
        raise AssertionError("should not call the activity")

    monkeypatch.setattr(tw, "execute_activity", boom)

    try:
        await ep.enrich(_ctx(), _phase(on_failure="explode"), _state(with_case=True))
        raise AssertionError("expected ApplicationError")
    except ApplicationError as exc:
        expect(exc.type).to(equal(ENRICH_CONFIG_ERROR_TYPE))


async def test_enrich__activity_config_error_propagates_without_review(monkeypatch):
    cause = ApplicationError("args do not match input_schema", type=ENRICH_CONFIG_ERROR_TYPE, non_retryable=True)
    calls: list = []
    _router(
        monkeypatch,
        {"tool_lookup": _activity_error(cause), "dispatch_case_event": True},
        calls,
    )

    try:
        await ep.enrich(_ctx(), _phase(), _state(with_case=True))
        raise AssertionError("expected ApplicationError")
    except ApplicationError as exc:
        expect(exc.type).to(equal(ENRICH_CONFIG_ERROR_TYPE))
        expect(str(exc)).to(contain("misconfigured"))

    # case.failed best-effort, never a review task for config errors.
    expect([name for name, *_ in calls]).to(equal(["tool_lookup", "dispatch_case_event"]))


async def test_enrich__activity_infra_error_takes_on_failure_path(monkeypatch):
    calls: list = []
    _router(
        monkeypatch,
        {
            "tool_lookup": _activity_error(RuntimeError("timeout")),
            "create_human_task": SimpleNamespace(task_id=uuid4(), task_key="k"),
        },
        calls,
    )
    state = _state(with_case=True)

    await ep.enrich(_ctx(), _phase(), state)  # default review → continues

    expect(state.scratch["enrichment"]["lookup_poliza"]["status"]).to(equal("DEGRADED"))
    expect(state.scratch["enrichment"]["lookup_poliza"]["error"]).to(contain("activity_failed"))
    expect([name for name, *_ in calls]).to(equal(["tool_lookup", "create_human_task"]))
