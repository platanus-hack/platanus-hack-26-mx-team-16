"""Rate-limit invariant (01-legal §2.5, §4) — constant contract + live Redis check.

Invariant: the API rate limit is 5 scans / 3600 s per user, enforced by REUSING
the existing Redis ``RateLimiter`` (fixed_window), not slowapi. The end-to-end
``POST /scans`` -> 429 + ``Retry-After`` test is owned by 12-api (the endpoint);
here we pin the shared constant and prove the existing limiter yields the 6th
request over the same key (the orchestrator runs the Redis-backed part).
"""

from __future__ import annotations

import pytest
from expects import be_above, equal, expect

from src.common.domain.legal.constants import API_SCAN_RATE_LIMIT


def test_api_scan_rate_limit_constant() -> None:
    limit, window = API_SCAN_RATE_LIMIT
    expect(limit).to(equal(5))
    expect(window).to(equal(3600))
    expect(window).to(be_above(0))


@pytest.mark.api
async def test_sixth_scan_in_window_is_blocked() -> None:
    """Live Redis: the 6th request for the same user key is denied (429 source).

    Requires Redis (docker). The 12-api endpoint test wires this into
    ``POST /scans`` and asserts the 429 + ``Retry-After`` response; this proves
    the underlying limiter, configured from ``API_SCAN_RATE_LIMIT``, blocks the
    6th call.
    """
    from redis.asyncio import Redis

    from src.common.infrastructure.services.rate_limiter import (
        RateLimiter,
        RateLimitExceededError,
    )
    from src.common.settings import settings

    limit, window = API_SCAN_RATE_LIMIT
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    limiter = RateLimiter(redis)
    key = "scans:test-user-legal-invariant"
    # The fixed_window strategy stores the counter under ``rate_limit:fixed:{key}``
    # (see RateLimiter._fixed_window). Clear that exact key so a counter left over
    # from a previously crashed run cannot pre-block the first request here.
    await redis.delete(f"rate_limit:fixed:{key}")

    try:
        # The first ``limit`` calls are allowed and return ``allowed=True``.
        for _ in range(limit):
            allowed, _remaining, _reset = await limiter.check_rate_limit(
                key=key, limit=limit, window=window, strategy="fixed_window"
            )
            expect(allowed).to(equal(True))

        # The (limit+1)-th call is blocked. The limiter signals denial by
        # RAISING ``RateLimitExceededError`` (the 429 source the endpoint relies
        # on), not by returning ``allowed=False``.
        with pytest.raises(RateLimitExceededError):
            await limiter.check_rate_limit(
                key=key, limit=limit, window=window, strategy="fixed_window"
            )
    finally:
        await limiter.reset_rate_limit(key)
        await redis.aclose()
