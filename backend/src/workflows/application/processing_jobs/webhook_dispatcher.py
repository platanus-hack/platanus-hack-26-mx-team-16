"""Transport seam for delivering a signed webhook (spec §4.6).

Mirrors ``analysis_run_summary/webhook_dispatcher.py``. The use case owns
persistence/orchestration; the dispatcher only signs + POSTs and reports the
result, so it stays trivially fakeable in tests and reusable for ANALYSIS.
"""

from __future__ import annotations

from typing import Protocol

from src.common.application.helpers.webhooks.delivery import WebhookDeliveryResult
from src.common.application.logging import get_logger

logger = get_logger(__name__)


class WorkflowWebhookDispatcher(Protocol):
    async def deliver(
        self,
        *,
        url: str,
        secret: str,
        event_id: str,
        body: str,
        timestamp: int,
    ) -> WebhookDeliveryResult: ...


class NoopWorkflowWebhookDispatcher:
    """Default dispatcher — logs and reports a non-delivery (replace once wired)."""

    async def deliver(self, **kwargs: object) -> WebhookDeliveryResult:
        logger.info("workflow_webhook.dispatch_noop", event_id=kwargs.get("event_id"))
        return WebhookDeliveryResult(
            delivered=False,
            attempts=0,
            status_code=None,
            error="webhook dispatcher not configured",
        )
