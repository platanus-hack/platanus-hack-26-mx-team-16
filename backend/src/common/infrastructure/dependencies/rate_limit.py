from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis

from src.common.infrastructure.services.rate_limiter import (
    RateLimiter,
    RateLimitExceededError,
    RateLimitStrategy,
)


def get_redis_client(request: Request) -> Redis:
    """Get Redis client from app state"""
    return request.app.state.redis_client


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""

    limit: int  # Maximum requests allowed
    window: int  # Time window in seconds
    strategy: RateLimitStrategy = "fixed_window"
    key_func: Callable[[Request], str] | None = None  # Custom key function


def create_rate_limit_dependency(
    limit: int,
    window: int,
    strategy: RateLimitStrategy = "fixed_window",
    key_func: Callable[[Request], str] | None = None,
):
    """
    Create a FastAPI dependency for rate limiting.

    Args:
        limit: Maximum number of requests allowed
        window: Time window in seconds
        strategy: Rate limiting strategy ("fixed_window" or "sliding_window")
        key_func: Optional function to generate custom rate limit key from request

    Usage:
        # Rate limit by IP address (10 requests per minute)
        rate_limit_dep = create_rate_limit_dependency(limit=10, window=60)

        @router.get("/endpoint")
        async def my_endpoint(
            _: Annotated[None, Depends(rate_limit_dep)]
        ):
            return {"message": "success"}

        # Rate limit by user ID (100 requests per hour)
        def by_user(request: Request) -> str:
            return f"user:{request.state.user_id}"

        rate_limit_user = create_rate_limit_dependency(
            limit=100,
            window=3600,
            key_func=by_user
        )
    """

    async def rate_limit_dependency(
        request: Request,
        redis_client: Annotated[Redis, Depends(get_redis_client)],
    ) -> None:
        # Generate rate limit key
        if key_func:
            key = key_func(request)
        else:
            # Default: use IP address
            client_ip = request.client.host if request.client else "unknown"
            key = f"ip:{client_ip}:{request.url.path}"

        # Check rate limit
        rate_limiter = RateLimiter(redis_client=redis_client)

        try:
            allowed, remaining, _ = await rate_limiter.check_rate_limit(
                key=key, limit=limit, window=window, strategy=strategy
            )

            # Add rate limit headers to response
            request.state.rate_limit_limit = limit
            request.state.rate_limit_remaining = remaining
            request.state.rate_limit_window = window

        except RateLimitExceededError as e:
            # Headers will be added by exception handler
            request.state.rate_limit_limit = e.limit
            request.state.rate_limit_remaining = 0
            request.state.rate_limit_retry_after = e.retry_after
            raise

    return rate_limit_dependency


# Common rate limit presets
RateLimitStrict = create_rate_limit_dependency(limit=10, window=60)  # 10/min
RateLimitModerate = create_rate_limit_dependency(limit=60, window=60)  # 60/min
RateLimitGenerous = create_rate_limit_dependency(limit=100, window=60)  # 100/min
RateLimitPublic = create_rate_limit_dependency(limit=20, window=60)  # 20/min for public endpoints


# Type aliases for easier usage
RateLimitStrictDep = Annotated[None, Depends(RateLimitStrict)]
RateLimitModerateDep = Annotated[None, Depends(RateLimitModerate)]
RateLimitGenerousDep = Annotated[None, Depends(RateLimitGenerous)]
RateLimitPublicDep = Annotated[None, Depends(RateLimitPublic)]
