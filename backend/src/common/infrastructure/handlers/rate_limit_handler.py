from fastapi import Request, status
from fastapi.responses import JSONResponse

from src.common.infrastructure.services.rate_limiter import RateLimitExceededError


async def rate_limit_exception_handler(request: Request, exc: RateLimitExceededError) -> JSONResponse:
    """Handle rate limit exceeded errors"""

    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded",
            "message": str(exc),
            "limit": exc.limit,
            "window": exc.window,
            "retry_after": exc.retry_after,
        },
    )

    # Add standard rate limit headers
    response.headers["X-RateLimit-Limit"] = str(exc.limit)
    response.headers["X-RateLimit-Remaining"] = "0"
    response.headers["X-RateLimit-Reset"] = str(exc.retry_after)
    response.headers["Retry-After"] = str(exc.retry_after)

    return response
