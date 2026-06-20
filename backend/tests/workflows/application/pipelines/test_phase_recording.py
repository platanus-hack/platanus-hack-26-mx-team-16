"""Unit tests for the per-phase recording hook of ``execute_pipeline``.

These prove the "Ejecuciones" mechanism in isolation: the ``on_phase`` observer
fires STARTED→COMPLETED per phase (FAILED + re-raise on error), and — critically
— that omitting the observer touches NOTHING extra (no ``workflow.now``, no
recording), which is what keeps the legacy-parity golden byte-identical.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from expects import be_none, equal, expect
from temporalio import workflow as tw

from src.common.domain.enums.pipelines import PhaseKind
from src.workflows.application.pipelines import runtime
from src.workflows.application.pipelines.runtime import (
    PipelineState,
    execute_pipeline,
    phase_output_snapshot,
)
from src.workflows.domain.models.pipeline import PhaseSpec

_DT = datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC)


def _state() -> PipelineState:
    # Handlers below never read ``data``; a stub keeps the unit pure.
    return PipelineState(data=None, job_id="JOB#1")


async def _ok_handler(ctx, phase, state):  # noqa: ANN001
    state.put_artifact(phase.kind.value, {"output_uri": f"s3://x/{phase.id}"})


async def _boom_handler(ctx, phase, state):  # noqa: ANN001
    raise RuntimeError("kaput")


async def test_on_phase__fires_started_then_completed_per_phase(monkeypatch):
    # Arrange
    monkeypatch.setattr(tw, "now", lambda: _DT)
    monkeypatch.setitem(runtime.PHASE_LIBRARY, "ingest", _ok_handler)
    monkeypatch.setitem(runtime.PHASE_LIBRARY, "finalize", _ok_handler)
    phases = [
        PhaseSpec(id="a", kind=PhaseKind.INGEST),
        PhaseSpec(id="b", kind=PhaseKind.FINALIZE),
    ]
    events: list = []

    async def rec(event, index, phase, state, started, error):  # noqa: ANN001
        events.append((event, index, phase.id))

    # Act
    await execute_pipeline(object(), phases, _state(), on_phase=rec)

    # Assert — strict ordering, bracketed per phase
    expect(events).to(
        equal(
            [
                ("STARTED", 0, "a"),
                ("COMPLETED", 0, "a"),
                ("STARTED", 1, "b"),
                ("COMPLETED", 1, "b"),
            ]
        )
    )


async def test_on_phase__records_failed_and_reraises(monkeypatch):
    # Arrange
    monkeypatch.setattr(tw, "now", lambda: _DT)
    monkeypatch.setitem(runtime.PHASE_LIBRARY, "ingest", _boom_handler)
    phases = [PhaseSpec(id="a", kind=PhaseKind.INGEST)]
    events: list = []

    async def rec(event, index, phase, state, started, error):  # noqa: ANN001
        events.append((event, error))

    # Act / Assert — the original error still propagates unchanged
    with pytest.raises(RuntimeError):
        await execute_pipeline(object(), phases, _state(), on_phase=rec)

    expect([e[0] for e in events]).to(equal(["STARTED", "FAILED"]))
    expect(events[1][1]["message"]).to(equal("kaput"))


async def test_no_observer__never_touches_workflow_now(monkeypatch):
    # Arrange — deliberately DO NOT patch tw.now: if execute_pipeline called it
    # with on_phase=None (outside the sandbox) it would raise. This is the
    # golden-parity guard expressed as a unit test.
    monkeypatch.setitem(runtime.PHASE_LIBRARY, "ingest", _ok_handler)
    phases = [PhaseSpec(id="a", kind=PhaseKind.INGEST)]

    # Act
    state = await execute_pipeline(object(), phases, _state())

    # Assert — pipeline ran, no recording machinery invoked
    expect(state.artifact("ingest")).to(equal({"output_uri": "s3://x/a"}))


def test_phase_output_snapshot__wraps_artifact_under_its_key():
    state = _state()
    state.put_artifact("extract_text", {"output_uri": "s3://x"})

    snap = phase_output_snapshot(
        PhaseSpec(id="t", kind=PhaseKind.EXTRACT_TEXT), state
    )

    expect(snap).to(equal({"key": "extract_text", "value": {"output_uri": "s3://x"}}))


def test_phase_output_snapshot__none_when_phase_wrote_nothing():
    snap = phase_output_snapshot(PhaseSpec(id="t", kind=PhaseKind.EXTRACT_TEXT), _state())

    expect(snap).to(be_none)


def test_phase_output_snapshot__truncates_oversize_artifact():
    state = _state()
    state.put_artifact("extract_fields", {"big": "x" * 20000})

    snap = phase_output_snapshot(
        PhaseSpec(id="t", kind=PhaseKind.EXTRACT_FIELDS), state
    )

    expect(snap.get("truncated")).to(equal(True))
