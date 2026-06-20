"""HTTP implementation of ``WorkflowWebhookDispatcher`` (spec §4.6/§4.7).

Thin adapter over the shared ``deliver_webhook`` helper (sign + POST + bounded
per-POST retry). The use case persists the outcome on the ``WorkflowEvent``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.common.application.helpers.webhooks.delivery import (
    WebhookDeliveryResult,
    deliver_webhook,
)

if TYPE_CHECKING:
    import httpx


class HttpWorkflowWebhookDispatcher:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def deliver(
        self,
        *,
        url: str,
        secret: str,
        event_id: str,
        body: str,
        timestamp: int,
    ) -> WebhookDeliveryResult:
        return await deliver_webhook(
            url=url,
            body=body,
            secret=secret,
            event_id=event_id,
            timestamp=timestamp,
            client=self._client,
        )
