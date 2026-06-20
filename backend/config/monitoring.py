import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from src.common.application.logging import get_logger
from src.common.settings import settings

logger = get_logger(__name__)


def init_sentry() -> None:
    """
    Initialize Sentry SDK for error tracking and performance monitoring.

    This function sets up Sentry with FastAPI, Starlette, Redis, and SQLAlchemy integrations.
    It only initializes if SENTRY_DSN is configured and the environment is not local.

    For more information, see:
    - https://docs.sentry.io/platforms/python/integrations/fastapi/
    - https://docs.sentry.io/platforms/python/configuration/options/
    """
    if not settings.sentry_enabled:
        logger.info("sentry.disabled", environment=str(settings.ENVIRONMENT))
        return

    try:
        sentry_sdk.init(
            dsn=str(settings.SENTRY_DSN),
            environment=str(settings.SENTRY_ENVIRONMENT),
            # Performance Monitoring
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
            # Integrations
            integrations=[
                StarletteIntegration(
                    transaction_style="endpoint",
                    failed_request_status_codes={403, *range(500, 599)},
                ),
                FastApiIntegration(
                    transaction_style="endpoint",
                    failed_request_status_codes={403, *range(500, 599)},
                ),
                RedisIntegration(),
                SqlalchemyIntegration(),
            ],
            # General Options
            attach_stacktrace=True,
            send_default_pii=settings.SENTRY_SEND_DEFAULT_PII,
            release=f"{settings.PROJECT_NAME}@{settings.VERSION}",
            server_name=settings.PROCESS_LABEL.value,
            max_breadcrumbs=50,
            # Feature Flags
            enable_tracing=True,
            auto_session_tracking=True,
            # Request Body Capture
            max_request_body_size="medium",  # Captures up to 10KB
            # Before Send Hook (optional - for filtering events)
            before_send=before_send,
        )
        logger.info(
            "sentry.initialized",
            environment=str(settings.SENTRY_ENVIRONMENT),
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        )
    except Exception as e:
        logger.error("sentry.initialization_failed", error=str(e))


def before_send(event: dict, hint: dict) -> dict | None:
    """
    Hook called before sending events to Sentry.

    This function can be used to:
    - Filter out events that shouldn't be sent
    - Modify event data before sending
    - Add custom tags or context

    Args:
        event: The event dictionary to be sent
        hint: Additional information about the event

    Returns:
        The modified event dictionary, or None to drop the event
    """
    # Example: Filter out events from health check endpoints
    if "request" in event:
        url = event["request"].get("url", "")
        if any(path in url for path in ["/health", "/healthz", "/readyz"]):
            return None

    # Example: Add custom tags
    event.setdefault("tags", {})
    event["tags"]["app"] = settings.PROJECT_NAME

    return event
