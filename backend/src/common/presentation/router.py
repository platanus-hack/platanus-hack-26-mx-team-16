from fastapi import APIRouter, HTTPException

from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.common.presentation.endpoints.health import health, ready
from src.common.settings import settings

common_router = APIRouter()

# Liveness/readiness — public, no auth (12-api §6).
common_router.add_api_route(
    "/health",
    health,
    methods=["GET"],
    summary="Process liveness (public)",
)
common_router.add_api_route(
    "/ready",
    ready,
    methods=["GET"],
    summary="Readiness — Postgres + Redis connectivity (public)",
)


@common_router.get("/")
async def home():
    return ApiJSONResponse(
        content={
            "status": "OK",
        }
    )


@common_router.get("/sentry-debug")
async def sentry_debug():
    """
    Test endpoint to verify Sentry integration.

    This endpoint intentionally raises an exception to test error tracking.
    Use it to verify that errors are being sent to Sentry correctly.

    Only available in development environment.

    Example:
        GET /sentry-debug

    Raises:
        HTTPException: Always raises a 500 error for testing
    """
    if not settings.ENVIRONMENT.is_local:
        raise HTTPException(
            status_code=404,
            detail="Endpoint only available in development",
        )

    # This will trigger a Sentry error
    division_by_zero = 1 / 0
    return {"message": "This should never be reached"}
