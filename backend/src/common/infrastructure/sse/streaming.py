"""Reusable SSE streaming helper built on Redis Pub/Sub.

Every module that needs an SSE endpoint composes the same pieces:
ownership check → ``return stream_sse(...)``. The helper handles the
wire format, the ``ready`` opener, the ``heartbeat`` keep-alive, the
optional replay window, and the optional filter callback. Endpoints stay
thin and consistent.

"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable, Collection
from typing import Any

from fastapi import Request
from redis.asyncio import Redis
from redis.asyncio.client import PubSub
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from src.common.application.logging import get_logger

logger = get_logger(__name__)

ReplayFn = Callable[[], AsyncIterator[dict[str, Any]]]
FilterFn = Callable[[dict[str, Any]], bool]


def _seq_id(ev: dict[str, Any]) -> str | None:
    """SSE ``id:`` for an event = its ``seq`` (the per-scan cursor), or ``None``.

    Returns ``None`` when the event has no ``seq`` (e.g. other callers whose
    events are namespaced differently), so this never breaks them: the ``id:``
    line is only emitted when a ``seq`` is present. A native ``EventSource``
    tracks this ``id`` and re-sends it as ``Last-Event-ID`` on reconnect,
    closing the replay loop without loss.
    """
    seq = ev.get("seq")
    return str(seq) if seq is not None else None


async def _frames(
    pubsub: PubSub,
    request: Request,
    *,
    replay: ReplayFn | None,
    filter_fn: FilterFn | None,
    close_after: Collection[str] | None,
    heartbeat_s: float,
) -> AsyncIterator[ServerSentEvent]:
    yield ServerSentEvent(event="ready", data="{}")

    if replay is not None:
        async for ev in replay():
            yield ServerSentEvent(
                event=str(ev.get("type", "message")),
                id=_seq_id(ev),
                data=json.dumps(ev),
            )

    # Dedupe between replay and live is the caller's responsibility via
    # ``filter_fn``. The previous implementation kept a global seq set,
    # but per-channel seqs are namespaced (e.g. processing_job events use
    # a `(processing_job_id, seq)` tuple), so a flat int set produced false
    # positives — a terminal event from set B could collide with a
    # replayed seq from set A and get dropped, leaving the live UI stuck.

    while True:
        if await request.is_disconnected():
            return
        # `get_message(timeout=X)` returns None on idle — no need to wrap in wait_for.
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=heartbeat_s)
        if message is None:
            yield ServerSentEvent(event="heartbeat", data="{}")
            continue
        raw = message.get("data")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if not isinstance(raw, str):
            continue
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("sse.stream.invalid_payload", raw=raw[:200])
            continue
        if filter_fn is not None and not filter_fn(ev):
            continue
        event_type = str(ev.get("type", "message"))
        yield ServerSentEvent(event=event_type, id=_seq_id(ev), data=raw)
        if close_after is not None and event_type in close_after:
            return


def stream_sse(
    *,
    channel: str,
    redis_client: Redis,
    request: Request,
    replay: ReplayFn | None = None,
    filter_fn: FilterFn | None = None,
    close_after: Collection[str] | None = None,
    heartbeat_s: float = 15.0,
) -> EventSourceResponse:
    """Subscribe to ``channel`` and stream events to the client as SSE.

    Args:
        channel: Redis pub/sub channel to subscribe to.
        redis_client: shared Redis client (``app.state.redis_client``).
        request: incoming FastAPI request, used to detect client disconnects.
        replay: optional callable returning an async-iterator of replayed
            event dicts (e.g. from a Postgres window). Live events are NOT
            deduped against the replay — clients dedupe by ``seq``.
        filter_fn: optional predicate over each live event dict; ``False``
            drops the event.
        close_after: optional set of terminal event types that close the
            stream after being delivered (e.g. ``RUN_COMPLETED``).
        heartbeat_s: idle interval after which a ``heartbeat`` frame is
            emitted to keep proxies from killing the connection.
    """

    async def gen() -> AsyncIterator[ServerSentEvent]:
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for frame in _frames(
                pubsub,
                request,
                replay=replay,
                filter_fn=filter_fn,
                close_after=close_after,
                heartbeat_s=heartbeat_s,
            ):
                yield frame
        finally:
            try:
                await pubsub.unsubscribe(channel)
            finally:
                await pubsub.aclose()

    return EventSourceResponse(
        gen(),
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
