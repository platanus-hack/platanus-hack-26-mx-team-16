"""
Structlog configuration for production-ready structured logging.

Features:
- JSON output for production
- Colored console output for development
- Request correlation IDs
- Performance metrics (duration tracking)
- Consistent event naming: domain.action.state
"""

import logging
import sys
from typing import Any

import structlog
from structlog.typing import EventDict, WrappedLogger

from src.common.settings import settings


def add_app_context(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Add application context to all log events."""
    event_dict["environment"] = settings.ENVIRONMENT.value
    event_dict["stage"] = settings.STAGE.value
    event_dict["process"] = settings.PROCESS_LABEL.value
    event_dict["version"] = settings.VERSION
    return event_dict


def add_log_level_name(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Add log level name for easier filtering."""
    event_dict["level"] = method_name.upper()
    return event_dict


def drop_debug_in_production(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Drop debug logs in production for performance."""
    if settings.ENVIRONMENT.is_production and method_name == "debug":
        raise structlog.DropEvent
    return event_dict


def extract_from_record(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """
    Extract extra information from standard library logging.
    Allows compatibility with libraries using stdlib logging.
    """
    record = event_dict.get("_record")
    if record:
        event_dict["logger_name"] = record.name
        event_dict["line"] = record.lineno
        event_dict["function"] = record.funcName

    return event_dict


def configure_logging() -> None:
    """
    Configure structlog with appropriate processors for the environment.

    Development: Colored console output with human-readable format
    Production: JSON output for log aggregation systems
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    )

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Determine output format based on environment
    if settings.ENVIRONMENT.is_production:
        # Production: JSON for machine parsing
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: Colored console for human readability
        renderer = structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.plain_traceback,
        )

    # Shared processors for all environments
    shared_processors: list[Any] = [
        # Add context
        structlog.contextvars.merge_contextvars,
        add_app_context,
        add_log_level_name,
        drop_debug_in_production,
        # Add timestamps
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Stack info for errors
        structlog.processors.StackInfoRenderer(),
        # Exception formatting
        structlog.processors.format_exc_info,
        # Unicode handling
        structlog.processors.UnicodeDecoder(),
    ]

    # Configure structlog
    structlog.configure(
        processors=[
            # Filter by log level
            structlog.stdlib.filter_by_level,
            *shared_processors,
            # Standard library compatibility
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to use structlog
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            extract_from_record,
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Configured structlog logger

    Example:
        logger = get_logger(__name__)
        logger.info("payment_intent.sync.started", provider_id="pi_123", tenant_id=tenant_id)
    """
    return structlog.get_logger(name)


# Event naming helpers for consistency
class LogEvent:
    """
    Helper class to ensure consistent event naming.
    Format: domain.action.state

    Usage:
        logger.info(LogEvent.payment_intent_sync_started(), provider_id="pi_123")
    """

    # Webhook events
    @staticmethod
    def webhook_received() -> str:
        return "webhook.received"

    @staticmethod
    def webhook_signature_verified() -> str:
        return "webhook.signature.verified"

    @staticmethod
    def webhook_signature_failed() -> str:
        return "webhook.signature.failed"

    @staticmethod
    def webhook_duplicate_detected() -> str:
        return "webhook.duplicate.detected"

    @staticmethod
    def webhook_enqueued() -> str:
        return "webhook.enqueued"

    @staticmethod
    def webhook_processing_started() -> str:
        return "webhook.processing.started"

    @staticmethod
    def webhook_processing_completed() -> str:
        return "webhook.processing.completed"

    @staticmethod
    def webhook_processing_failed() -> str:
        return "webhook.processing.failed"

    # Payment Intent events
    @staticmethod
    def payment_intent_sync_started() -> str:
        return "payment_intent.sync.started"

    @staticmethod
    def payment_intent_sync_completed() -> str:
        return "payment_intent.sync.completed"

    @staticmethod
    def payment_intent_sync_failed() -> str:
        return "payment_intent.sync.failed"

    @staticmethod
    def payment_intent_sync_skipped_stale() -> str:
        return "payment_intent.sync.skipped_stale"

    @staticmethod
    def payment_intent_created() -> str:
        return "payment_intent.created"

    @staticmethod
    def payment_intent_updated() -> str:
        return "payment_intent.updated"

    @staticmethod
    def payment_intent_persist_failed() -> str:
        return "payment_intent.persist.failed"

    # Payment Charge events
    @staticmethod
    def payment_charge_sync_started() -> str:
        return "payment_charge.sync.started"

    @staticmethod
    def payment_charge_sync_completed() -> str:
        return "payment_charge.sync.completed"

    @staticmethod
    def payment_charge_sync_failed() -> str:
        return "payment_charge.sync.failed"

    @staticmethod
    def payment_charge_sync_skipped_stale() -> str:
        return "payment_charge.sync.skipped_stale"

    @staticmethod
    def payment_charge_created() -> str:
        return "payment_charge.created"

    @staticmethod
    def payment_charge_updated() -> str:
        return "payment_charge.updated"

    # Lock events
    @staticmethod
    def lock_acquire_started() -> str:
        return "lock.acquire.started"

    @staticmethod
    def lock_acquire_completed() -> str:
        return "lock.acquire.completed"

    @staticmethod
    def lock_acquire_timeout() -> str:
        return "lock.acquire.timeout"

    @staticmethod
    def lock_acquire_contention() -> str:
        return "lock.acquire.contention"

    @staticmethod
    def lock_released() -> str:
        return "lock.released"

    # Provider API events
    @staticmethod
    def stripe_api_call_started() -> str:
        return "stripe.api.call.started"

    @staticmethod
    def stripe_api_call_completed() -> str:
        return "stripe.api.call.completed"

    @staticmethod
    def stripe_api_call_failed() -> str:
        return "stripe.api.call.failed"

    # Database events
    @staticmethod
    def db_query_started() -> str:
        return "db.query.started"

    @staticmethod
    def db_query_completed() -> str:
        return "db.query.completed"

    @staticmethod
    def db_transaction_started() -> str:
        return "db.transaction.started"

    @staticmethod
    def db_transaction_committed() -> str:
        return "db.transaction.committed"

    @staticmethod
    def db_transaction_rolled_back() -> str:
        return "db.transaction.rolled_back"

    # Optimistic lock events
    @staticmethod
    def optimistic_lock_conflict() -> str:
        return "optimistic_lock.conflict"

    @staticmethod
    def optimistic_lock_retry() -> str:
        return "optimistic_lock.retry"

    # Duplicate detection events
    @staticmethod
    def duplicate_detected() -> str:
        return "duplicate.detected"

    @staticmethod
    def duplicate_prevented() -> str:
        return "duplicate.prevented"
