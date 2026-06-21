"""Liveness / readiness endpoints (12-api §6). Both public, no auth.

- ``GET /health`` — process liveness; touches no dependency, always 200.
- ``GET /ready``  — readiness; pings Postgres (``SELECT 1``) and Redis (``PING``)
  via their own dependencies (``AppContext`` carries neither). 200 if both
  answer, **503** if either fails. Useful for orchestrators and the demo panel.
"""

from __future__ import annotations

from fastapi import status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.infrastructure.dependencies.common import (
    AsyncSessionDep,
    RedisClientDep,
)
from src.common.infrastructure.responses.api_json import ApiJSONResponse


async def health() -> ApiJSONResponse:
    return ApiJSONResponse(
        content={"status": "ok"},
        status_code=status.HTTP_200_OK,
    )


async def _ping_postgres(session: AsyncSession) -> bool:
    try:
        await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _ping_redis(redis_client: Redis) -> bool:
    try:
        pong = await redis_client.ping()
        return bool(pong)
    except Exception:
        return False


async def ready(
    session: AsyncSessionDep,
    redis_client: RedisClientDep,
) -> ApiJSONResponse:
    postgres_ok = await _ping_postgres(session)
    redis_ok = await _ping_redis(redis_client)
    all_ok = postgres_ok and redis_ok
    return ApiJSONResponse(
        content={
            "status": "ready" if all_ok else "not_ready",
            "checks": {"postgres": postgres_ok, "redis": redis_ok},
        },
        status_code=status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
