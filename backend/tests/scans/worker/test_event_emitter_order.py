"""``ScanEventEmitter`` contract (10 §3): PG-before-Redis, monotonic seq, terminals.

Pure unit tests with a mocked repo + Redis — the invariant is verified by the
recorded call order, not by a live stack.
"""

from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4

import pytest
from expects import be_below, equal, expect

from src.scans.domain.contracts.events import ScanEvent
from src.scans.worker.events import ScanEventEmitter


def _emitter():
    repo = MagicMock()
    repo.append = AsyncMock(side_effect=lambda ev: ev)
    redis = MagicMock()
    redis.publish = AsyncMock()
    return ScanEventEmitter(scan_id=uuid4(), repo=repo, redis=redis), repo, redis


async def test_emit_appends_to_postgres_before_publishing_to_redis():
    emitter, repo, redis = _emitter()
    # A single recorder captures the interleaving of both calls.
    order: list[str] = []
    repo.append = AsyncMock(side_effect=lambda ev: order.append("pg") or ev)
    redis.publish = AsyncMock(side_effect=lambda *a, **k: order.append("redis"))

    await emitter.emit("phase", message="scanning", agent="worker")

    expect(order).to(equal(["pg", "redis"]))


async def test_emit_assigns_monotonic_seq_per_scan():
    emitter, repo, _ = _emitter()

    await emitter.emit("phase", message="a", agent="worker")
    await emitter.emit("phase", message="b", agent="worker")
    await emitter.emit("phase", message="c", agent="worker")

    seqs = [c.args[0].seq for c in repo.append.call_args_list]
    expect(seqs).to(equal([1, 2, 3]))


async def test_emit_publishes_to_the_scan_events_channel():
    emitter, _, redis = _emitter()

    await emitter.emit("agent_status", message="hi", agent="worker")

    channel = redis.publish.call_args.args[0]
    expect(channel).to(equal(f"scan:{emitter.scan_id}:events"))


async def test_done_carries_outcome_in_payload():
    emitter, repo, _ = _emitter()

    await emitter.done("finished", outcome="cancelled")

    ev: ScanEvent = repo.append.call_args.args[0]
    expect(ev.type).to(equal("done"))
    expect(ev.payload.get("outcome")).to(equal("cancelled"))


async def test_done_defaults_to_success():
    emitter, repo, _ = _emitter()

    await emitter.done("finished")

    ev: ScanEvent = repo.append.call_args.args[0]
    expect(ev.payload.get("outcome")).to(equal("success"))


async def test_publish_propagates_repo_integrity_error_without_publishing():
    """A duplicate ``(scan_id, seq)`` must blow up in append and never reach Redis."""
    emitter, repo, redis = _emitter()
    repo.append = AsyncMock(side_effect=RuntimeError("UNIQUE (scan_id, seq)"))

    with pytest.raises(RuntimeError):
        await emitter.emit("phase", message="dup", agent="worker")

    redis.publish.assert_not_awaited()


async def test_low_level_publish_does_pg_then_redis():
    emitter, repo, redis = _emitter()
    order: list[str] = []
    repo.append = AsyncMock(side_effect=lambda ev: order.append("pg") or ev)
    redis.publish = AsyncMock(side_effect=lambda *a, **k: order.append("redis"))
    event = ScanEvent(
        scan_id=emitter.scan_id,
        seq=1,
        ts=__import__("datetime").datetime.now(__import__("datetime").UTC),
        type="phase",
        message="x",
    )

    await emitter.publish(emitter.scan_id, event)

    expect(order).to(equal(["pg", "redis"]))
