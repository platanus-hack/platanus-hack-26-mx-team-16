"""Postgres-backed replay window for the SSE live view (10 §4.1).

The replay is the half of *replay-then-tail* that reconstructs everything a
client missed between the scan start (or its last disconnect) and its
``SUBSCRIBE``. It reads ``scan_events WHERE seq > since_seq ORDER BY seq ASC``
from the **authoritative** Postgres table — never from Redis.

``make_scan_event_replay`` returns a ``ReplayFn`` (the shape ``stream_sse``
expects): a zero-arg callable yielding an ``AsyncIterator`` of plain event dicts.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from src.common.infrastructure.sse.streaming import ReplayFn
from src.scans.domain.repositories.scan_event import ScanEventRepository


async def make_scan_event_replay(
    repo: ScanEventRepository,
    scan_id: UUID,
    since_seq: int,
) -> ReplayFn:
    """Build the ``ReplayFn`` for ``scan_events`` with ``seq > since_seq``.

    ``since_seq=0`` ⇒ full replay from the start of the scan; ``since_seq=last``
    ⇒ empty (client is already caught up). Ordering is by ``seq`` ASC — the
    single source of order — regardless of insertion timing.

    CRITICAL (10 §4.1, SSE lifecycle): the Postgres read happens **eagerly here**,
    inside the request scope, NOT lazily when the stream generator iterates. The
    ``EventSourceResponse`` body runs *after* the endpoint returns and FastAPI has
    torn down the request-scoped DB session, so a deferred query would hit a
    closed connection and kill the generator right after the ``ready`` frame
    (the stream would open then immediately close). We materialize JSON-safe dicts
    up front and the returned ``ReplayFn`` only replays that in-memory snapshot.
    """
    events = await repo.replay(scan_id, after_seq=since_seq or None)
    # mode="json" → seq/type/ts/... as JSON-safe primitives for stream_sse.
    snapshot: list[dict[str, Any]] = [e.model_dump(mode="json") for e in events]

    async def replay() -> AsyncIterator[dict[str, Any]]:
        for event in snapshot:
            yield event

    return replay
