"""``GET /scans/{id}/stream`` — SSE live view DECLARATION (12-api §"SSE"; body in 10).

12-api owns only the **endpoint contract and the auth gate**; the replay-then-tail
body (Postgres replay of ``scan_events`` with ``seq > cursor`` from ``Last-Event-ID``
/ ``?since_seq=``, then Redis ``scan:{id}:events`` pub/sub tail, heartbeat, no
compression) is filled in by 10-realtime-live-view.

Auth gate (spec §"AuthZ por endpoint" + §"SSE"):
- ``public`` scans stream without auth.
- ``private`` scans require either the session (``EventSource`` is opened with
  ``withCredentials``; the cookie/bearer is validated via the optional auth
  dependency) **or** a single-use ``?stream_token=`` (the token scheme is owned by
  10). A private scan never streams open.

This declaration resolves+authorizes the scan and the cursor, then raises
``NotImplementedError`` until 10 supplies the streaming response. The route is
registered so the OpenAPI contract (and the frontend BFF) can target it now.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Query

from src.common.domain.enums.scans import ScanVisibility
from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.session import (
    get_optional_authenticated_user,
)
from src.scans.presentation.exceptions import ScanNotFoundError


async def stream_scan(
    scan_id: UUID,
    domain_context: DomainContextDep,
    user: Annotated[User | None, Depends(get_optional_authenticated_user)],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
    since_seq: Annotated[int | None, Query()] = None,
    stream_token: Annotated[str | None, Query()] = None,
):
    """Auth + cursor gate for the SSE stream. Streaming body supplied by 10."""
    scan = await domain_context.scan_repository.find(scan_id)
    if scan is None:
        raise ScanNotFoundError

    if scan.visibility != str(ScanVisibility.PUBLIC):
        # Private: require an authenticated owner OR a single-use stream token
        # (the token validation itself is owned by 10). Never confirm existence
        # to an unauthorized caller — 404, not 403.
        authorized = (
            user is not None
            and scan.requested_by is not None
            and scan.requested_by == user.uuid
        )
        if not authorized and stream_token is None:
            raise ScanNotFoundError

    # Resolve the replay cursor: Last-Event-ID (EventSource reconnect) wins, else
    # ?since_seq=. 10-realtime consumes this to replay scan_events then tail.
    cursor = since_seq
    if last_event_id is not None:
        try:
            cursor = int(last_event_id)
        except ValueError:
            cursor = since_seq

    # Body (replay-then-tail StreamingResponse) is provided by 10-realtime-live-view.
    raise NotImplementedError(
        "SSE replay-then-tail body is provided by 10-realtime-live-view; "
        f"this declaration authorized scan={scan_id} from cursor={cursor}."
    )
