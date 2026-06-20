"""Critical scenarios for the shared `stream_sse` SSE helper.

We drive `_frames` directly rather than `stream_sse` so we don't need
the FastAPI/sse-starlette response machinery — just the generator
behavior, which is what carries the contract.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from expects import equal, expect, have_length

from src.common.infrastructure.sse.streaming import _frames


@pytest.fixture
def request_mock():
    request = MagicMock()
    request.is_disconnected = AsyncMock(return_value=False)
    return request


def _make_pubsub(messages):
    """Create a pubsub mock whose `get_message` yields the given sequence.

    Each item is either a dict (a real message) or None (a heartbeat tick).
    The list is padded with disconnected=True after exhaustion so the
    generator terminates deterministically in tests that don't use
    `close_after`.
    """
    pubsub = MagicMock()
    pubsub.get_message = AsyncMock(side_effect=messages)
    return pubsub


def _live_message(payload: dict) -> dict:
    return {"type": "message", "data": json.dumps(payload)}


async def _drain(agen, max_frames: int = 50) -> list:
    """Collect up to `max_frames` from an async generator, then close it.

    Used for tests where the generator doesn't terminate on its own — we
    pull the expected number of frames and close.
    """
    frames = []
    try:
        for _ in range(max_frames):
            frames.append(await agen.__anext__())
    except StopAsyncIteration:
        pass
    finally:
        await agen.aclose()
    return frames


async def test_frames__emits_ready_first(request_mock):
    pubsub = _make_pubsub([None])
    # Disconnect right after the first heartbeat tick so we exit cleanly.
    request_mock.is_disconnected = AsyncMock(side_effect=[False, True])

    agen = _frames(pubsub, request_mock, replay=None, filter_fn=None, close_after=None, heartbeat_s=0.01)
    first = await agen.__anext__()
    await agen.aclose()

    expect(first.event).to(equal("ready"))


async def test_frames__yields_replay_events_before_live(request_mock):
    async def replay():
        yield {"seq": 1, "type": "REPLAYED", "payload": {}}
        yield {"seq": 2, "type": "REPLAYED", "payload": {}}

    pubsub = _make_pubsub([_live_message({"seq": 3, "type": "LIVE", "payload": {}})])
    request_mock.is_disconnected = AsyncMock(side_effect=[False, True])

    agen = _frames(pubsub, request_mock, replay=replay, filter_fn=None, close_after=None, heartbeat_s=0.01)
    frames = await _drain(agen, max_frames=4)

    expect([f.event for f in frames]).to(equal(["ready", "REPLAYED", "REPLAYED", "LIVE"]))


async def test_frames__heartbeat_when_pubsub_idle(request_mock):
    pubsub = _make_pubsub([None, None])
    request_mock.is_disconnected = AsyncMock(side_effect=[False, False, True])

    agen = _frames(pubsub, request_mock, replay=None, filter_fn=None, close_after=None, heartbeat_s=0.01)
    frames = await _drain(agen, max_frames=3)

    # ready + 2 heartbeats
    expect(frames).to(have_length(3))
    expect(frames[1].event).to(equal("heartbeat"))
    expect(frames[2].event).to(equal("heartbeat"))


async def test_frames__does_not_dedupe_live_event_against_replay(request_mock):
    """El dedupe replay↔live es responsabilidad del caller vía ``filter_fn``.

    ``_frames`` ya NO mantiene un set global de seqs: los seq son namespaced
    por canal (p. ej. ``(processing_job_id, seq)``) y un set plano de ints
    producía falsos positivos — un evento terminal del set B podía colisionar
    con un seq replayado del set A y dejar la UI colgada. El duplicado debe
    pasar; quien necesite dedupe lo expresa con ``filter_fn`` (test siguiente).
    """
    async def replay():
        yield {"seq": 99, "type": "ALREADY_SEEN", "payload": {}}

    pubsub = _make_pubsub(
        [
            _live_message({"seq": 99, "type": "ALREADY_SEEN", "payload": {}}),  # dup: pasa igual
            _live_message({"seq": 100, "type": "FRESH", "payload": {}}),
        ]
    )
    request_mock.is_disconnected = AsyncMock(side_effect=[False, False, True])

    agen = _frames(pubsub, request_mock, replay=replay, filter_fn=None, close_after=None, heartbeat_s=0.01)
    frames = await _drain(agen, max_frames=4)

    event_types = [f.event for f in frames]
    expect(event_types).to(equal(["ready", "ALREADY_SEEN", "ALREADY_SEEN", "FRESH"]))


async def test_frames__caller_dedupes_replay_overlap_via_filter_fn(request_mock):
    async def replay():
        yield {"seq": 99, "type": "ALREADY_SEEN", "payload": {}}

    pubsub = _make_pubsub(
        [
            _live_message({"seq": 99, "type": "ALREADY_SEEN", "payload": {}}),
            _live_message({"seq": 100, "type": "FRESH", "payload": {}}),
        ]
    )
    request_mock.is_disconnected = AsyncMock(side_effect=[False, False, True])
    replayed_seqs = {99}

    agen = _frames(
        pubsub,
        request_mock,
        replay=replay,
        filter_fn=lambda ev: ev.get("seq") not in replayed_seqs,
        close_after=None,
        heartbeat_s=0.01,
    )
    frames = await _drain(agen, max_frames=4)

    event_types = [f.event for f in frames]
    expect(event_types).to(equal(["ready", "ALREADY_SEEN", "FRESH"]))


async def test_frames__filter_fn_drops_event_when_returns_false(request_mock):
    pubsub = _make_pubsub(
        [
            _live_message({"seq": 1, "type": "KEEP", "payload": {}}),
            _live_message({"seq": 2, "type": "DROP", "payload": {}}),
            _live_message({"seq": 3, "type": "KEEP", "payload": {}}),
        ]
    )
    request_mock.is_disconnected = AsyncMock(side_effect=[False, False, False, True])

    def keep_only_keep(ev):
        return ev["type"] == "KEEP"

    agen = _frames(
        pubsub,
        request_mock,
        replay=None,
        filter_fn=keep_only_keep,
        close_after=None,
        heartbeat_s=0.01,
    )
    frames = await _drain(agen, max_frames=5)

    event_types = [f.event for f in frames]
    expect(event_types).to(equal(["ready", "KEEP", "KEEP"]))


async def test_frames__close_after_terminates_after_terminal_event(request_mock):
    pubsub = _make_pubsub(
        [
            _live_message({"seq": 1, "type": "RUN_PROGRESS", "payload": {}}),
            _live_message({"seq": 2, "type": "RUN_COMPLETED", "payload": {}}),
            # This one MUST NOT be delivered — stream should already be closed.
            _live_message({"seq": 3, "type": "EXTRA", "payload": {}}),
        ]
    )
    request_mock.is_disconnected = AsyncMock(return_value=False)

    agen = _frames(
        pubsub,
        request_mock,
        replay=None,
        filter_fn=None,
        close_after=frozenset({"RUN_COMPLETED"}),
        heartbeat_s=0.01,
    )
    frames = [frame async for frame in agen]

    event_types = [f.event for f in frames]
    expect(event_types).to(equal(["ready", "RUN_PROGRESS", "RUN_COMPLETED"]))


async def test_frames__client_disconnect_ends_loop(request_mock):
    pubsub = _make_pubsub(
        [
            _live_message({"seq": 1, "type": "FIRST", "payload": {}}),
        ]
    )
    # First check (after ready): connected. Second check: disconnected.
    request_mock.is_disconnected = AsyncMock(side_effect=[False, True])

    agen = _frames(pubsub, request_mock, replay=None, filter_fn=None, close_after=None, heartbeat_s=0.01)
    frames = [frame async for frame in agen]

    expect([f.event for f in frames]).to(equal(["ready", "FIRST"]))


async def test_frames__invalid_json_is_skipped_not_crashed(request_mock):
    pubsub = _make_pubsub(
        [
            {"type": "message", "data": "not-valid-json{"},
            _live_message({"seq": 1, "type": "AFTER_BAD", "payload": {}}),
        ]
    )
    request_mock.is_disconnected = AsyncMock(side_effect=[False, False, True])

    agen = _frames(pubsub, request_mock, replay=None, filter_fn=None, close_after=None, heartbeat_s=0.01)
    frames = await _drain(agen, max_frames=3)

    expect([f.event for f in frames]).to(equal(["ready", "AFTER_BAD"]))


async def test_frames__bytes_payload_is_decoded(request_mock):
    pubsub = _make_pubsub(
        [
            {
                "type": "message",
                "data": json.dumps({"seq": 1, "type": "BYTES", "payload": {}}).encode("utf-8"),
            },
        ]
    )
    request_mock.is_disconnected = AsyncMock(side_effect=[False, True])

    agen = _frames(pubsub, request_mock, replay=None, filter_fn=None, close_after=None, heartbeat_s=0.01)
    frames = await _drain(agen, max_frames=2)

    expect([f.event for f in frames]).to(equal(["ready", "BYTES"]))
