"""``GET /scans/{id}/stream`` — SSE live view (replay-then-tail) (10 §3–§4).

12-api declared the endpoint contract and the auth gate; **10 supplies the body**:
Postgres replay of ``scan_events`` with ``seq > cursor`` (from ``Last-Event-ID`` /
``?since_seq=``), then a Redis ``scan:{id}:events`` pub/sub tail, with a ~20s
heartbeat, ``done``/``error`` as terminal closers, and compression disabled (the
shared ``stream_sse`` helper already sets the anti-buffer headers
``Cache-Control: no-cache, no-transform`` + ``X-Accel-Buffering: no``).

Invariant guaranteed upstream (worker emitter, 10 §3): every event is persisted to
Postgres **before** it is published to Redis, so anything a client sees by tail is
already available for replay — never the reverse. The per-scan monotonic ``seq`` is
the sole source of order; the client dedupes the natural replay↔tail overlap by
dropping ``seq <= lastSeq`` (so ``filter_fn`` stays ``None`` here — dedupe is the
client's job, 10 §4.5).

Auth gate (spec §4, anti-IDOR from 12 §4):
- ``public`` scans stream without auth.
- ``private`` scans require an authenticated owner (session/bearer cookie) **or** a
  single-use ``?stream_token=``; otherwise **404, never 403** (existence is never
  confirmed to an unauthorized caller). A private scan never streams open.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Query, Request
from sse_starlette.sse import EventSourceResponse

from src.common.domain.enums.scans import ScanVisibility
from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import (
    DomainContextDep,
    RedisClientDep,
)
from src.common.infrastructure.dependencies.session import (
    get_optional_authenticated_user,
)
from src.common.infrastructure.sse.streaming import stream_sse
from src.scans.infrastructure.sse.channels import scan_events_channel
from src.scans.infrastructure.sse.replay import make_scan_event_replay
from src.scans.infrastructure.sse.stream_token import consume_stream_token
from src.scans.presentation.exceptions import ScanNotFoundError

#: Terminal event types that close the stream after delivery (spec §2).
TERMINAL_EVENT_TYPES = frozenset({"done", "error"})
#: Heartbeat interval — spec §3.2 (~20s; the client watchdog is comfortable ≥2×).
HEARTBEAT_SECONDS = 20.0


def _resolve_cursor(last_event_id: str | None, since_seq: int | None) -> int:
    """Replay cursor precedence (spec §3.1): ``Last-Event-ID`` > ``?since_seq=`` > 0.

    ``Last-Event-ID`` wins when present and numeric (the most recent cursor a
    reconnecting native ``EventSource`` knows); otherwise ``?since_seq=`` (the
    cursor the repo's fetch-based client sends); otherwise ``0`` = full replay.
    """
    if last_event_id is not None:
        try:
            return int(last_event_id)
        except ValueError:
            pass
    return since_seq or 0


async def stream_scan(
    scan_id: UUID,
    request: Request,
    redis_client: RedisClientDep,
    domain_context: DomainContextDep,
    user: Annotated[User | None, Depends(get_optional_authenticated_user)],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
    since_seq: Annotated[int | None, Query()] = None,
    stream_token: Annotated[str | None, Query()] = None,
) -> EventSourceResponse:
    """Replay-then-tail SSE live view for a scan (10 §3–§4)."""
    scan = await domain_context.scan_repository.find(scan_id)
    if scan is None:
        raise ScanNotFoundError

    if scan.visibility != str(ScanVisibility.PUBLIC):
        # Private: an authenticated owner, OR a valid single-use ?stream_token=.
        # Never confirm existence to an unauthorized caller — 404, not 403.
        authorized = (
            user is not None
            and scan.requested_by is not None
            and scan.requested_by == user.uuid
        )
        if not authorized and stream_token is not None:
            authorized = await consume_stream_token(
                redis_client, stream_token, scan_id
            )
        if not authorized:
            raise ScanNotFoundError

    # Resolve the replay cursor and read the PG replay window EAGERLY (await), while
    # the request-scoped DB session is still alive — the stream generator runs after
    # teardown, so a deferred read would hit a closed connection. Then replay-then-tail.
    cursor = _resolve_cursor(last_event_id, since_seq)
    replay = await make_scan_event_replay(
        domain_context.scan_event_repository, scan_id, cursor
    )
    return stream_sse(
        channel=scan_events_channel(scan_id),
        redis_client=redis_client,
        request=request,
        replay=replay,
        filter_fn=None,  # dedupe is the CLIENT's job (seq <= lastSeq) — 10 §4.5
        close_after=TERMINAL_EVENT_TYPES,  # done/error close the stream
        heartbeat_s=HEARTBEAT_SECONDS,
    )
