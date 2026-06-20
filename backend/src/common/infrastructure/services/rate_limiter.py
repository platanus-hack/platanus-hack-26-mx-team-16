from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from redis.asyncio import Redis

RateLimitStrategy = Literal["fixed_window", "sliding_window"]


@dataclass
class RateLimitExceededError(Exception):
    """Exception raised when rate limit is exceeded"""

    retry_after: int  # seconds until the limit resets
    limit: int  # the rate limit
    window: int  # the time window in seconds

    def __str__(self) -> str:
        return f"Rate limit exceeded. Limit: {self.limit} requests per {self.window}s. Retry after {self.retry_after}s"


@dataclass
class RateLimiter:
    """Rate limiter service using Redis"""

    redis_client: Redis

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int,
        strategy: RateLimitStrategy = "fixed_window",
    ) -> tuple[bool, int, int]:
        """
        Check if the rate limit has been exceeded.

        Args:
            key: Unique identifier for the rate limit (e.g., user_id, ip_address)
            limit: Maximum number of requests allowed
            window: Time window in seconds
            strategy: Rate limiting strategy to use

        Returns:
            tuple[allowed, remaining, retry_after]
                - allowed: Whether the request is allowed
                - remaining: Number of requests remaining in the current window
                - retry_after: Seconds until the limit resets (0 if allowed)

        Raises:
            RateLimitExceededError: If the rate limit is exceeded
        """
        if strategy == "sliding_window":
            return await self._sliding_window(key, limit, window)
        return await self._fixed_window(key, limit, window)

    async def _fixed_window(self, key: str, limit: int, window: int) -> tuple[bool, int, int]:
        """
        Fixed window rate limiting strategy.
        Simple and efficient but can allow bursts at window boundaries.
        """
        rate_limit_key = f"rate_limit:fixed:{key}"

        # Use Redis pipeline for atomic operations
        pipe = self.redis_client.pipeline()
        pipe.incr(rate_limit_key)
        pipe.expire(rate_limit_key, window)
        pipe.ttl(rate_limit_key)

        results = await pipe.execute()
        current_count = results[0]
        ttl = results[2]

        # If TTL is -1, the key exists but has no expiration (shouldn't happen with our logic)
        if ttl == -1:
            await self.redis_client.expire(rate_limit_key, window)
            ttl = window

        remaining = max(0, limit - current_count)
        allowed = current_count <= limit

        if not allowed:
            retry_after = ttl if ttl > 0 else window
            raise RateLimitExceededError(retry_after=retry_after, limit=limit, window=window)

        return allowed, remaining, 0

    async def _sliding_window(self, key: str, limit: int, window: int) -> tuple[bool, int, int]:
        """
        Sliding window rate limiting strategy.
        More accurate than fixed window but slightly more expensive.
        Uses sorted sets to track request timestamps.
        """
        rate_limit_key = f"rate_limit:sliding:{key}"
        now = datetime.now().timestamp()
        window_start = now - window

        pipe = self.redis_client.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(rate_limit_key, 0, window_start)

        # Count requests in the current window
        pipe.zcard(rate_limit_key)

        # Add current request with timestamp as score
        pipe.zadd(rate_limit_key, {str(now): now})

        # Set expiration
        pipe.expire(rate_limit_key, window)

        results = await pipe.execute()
        current_count = results[1]  # Count before adding current request

        remaining = max(0, limit - current_count - 1)
        allowed = current_count < limit

        if not allowed:
            # Calculate retry_after based on the oldest request in the window
            oldest_timestamp = await self.redis_client.zrange(rate_limit_key, 0, 0, withscores=True)
            if oldest_timestamp:
                oldest_time = oldest_timestamp[0][1]
                retry_after = int(oldest_time + window - now) + 1
            else:
                retry_after = window

            # Remove the request we just added since it's not allowed
            await self.redis_client.zrem(rate_limit_key, str(now))

            raise RateLimitExceededError(retry_after=retry_after, limit=limit, window=window)

        return allowed, remaining, 0

    async def reset_rate_limit(self, key: str, strategy: RateLimitStrategy = "fixed_window") -> None:
        """Reset rate limit for a specific key"""
        if strategy == "sliding_window":
            rate_limit_key = f"rate_limit:sliding:{key}"
        else:
            rate_limit_key = f"rate_limit:fixed:{key}"

        await self.redis_client.delete(rate_limit_key)

    async def get_rate_limit_info(self, key: str, strategy: RateLimitStrategy = "fixed_window") -> dict[str, int]:
        """Get current rate limit information for a key"""
        if strategy == "sliding_window":
            rate_limit_key = f"rate_limit:sliding:{key}"
            count = await self.redis_client.zcard(rate_limit_key)
        else:
            rate_limit_key = f"rate_limit:fixed:{key}"
            count_str = await self.redis_client.get(rate_limit_key)
            count = int(count_str) if count_str else 0

        ttl = await self.redis_client.ttl(rate_limit_key)

        return {"current_count": count, "ttl": ttl if ttl > 0 else 0}
