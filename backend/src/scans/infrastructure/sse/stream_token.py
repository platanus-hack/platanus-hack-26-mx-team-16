"""Ephemeral single-use ``stream_token`` for private-scan SSE (10 §5.2).

``EventSource``/``fetch`` cannot send custom headers, so a private scan that
can't ride the session cookie uses a short-lived query token instead. The token
is minted into Redis with a TTL and consumed with ``GETDEL`` (atomic single-use):
a replayed token fails. The token scheme is owned by 10; *who* mints it (a
dedicated endpoint or ``GET /scans/{id}`` returning it to the owner) is decided
by 12-api.
"""

from __future__ import annotations

import secrets

from redis.asyncio import Redis

#: Redis key prefix for minted stream tokens.
_STREAM_TOKEN_PREFIX = "stream_token:"
#: Default time-to-live (seconds) — short window bounds the blast radius.
DEFAULT_STREAM_TOKEN_TTL_S = 120


def _stream_token_key(token: str) -> str:
    return f"{_STREAM_TOKEN_PREFIX}{token}"


async def mint_stream_token(
    redis: Redis,
    scan_id: object,
    user_id: object,
    *,
    ttl_s: int = DEFAULT_STREAM_TOKEN_TTL_S,
) -> str:
    """Mint a single-use token bound to ``scan_id`` (and the requesting user).

    Returns the opaque token string; store nothing else client-side.
    """
    token = secrets.token_urlsafe(32)
    await redis.set(_stream_token_key(token), f"{scan_id}:{user_id}", ex=ttl_s)
    return token


async def consume_stream_token(redis: Redis, token: str, scan_id: object) -> bool:
    """Atomically consume ``token`` and return whether it authorizes ``scan_id``.

    ``GETDEL`` deletes the key as it reads it, so a second consume of the same
    token always returns ``False`` (single-use). A token minted for a *different*
    scan also returns ``False``.
    """
    raw = await redis.getdel(_stream_token_key(token))
    if raw is None:
        return False
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return raw.split(":", 1)[0] == str(scan_id)
