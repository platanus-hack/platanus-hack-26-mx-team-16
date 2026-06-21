"""Slack incoming-webhook alert sender (08-ranking-watchlists §5.1).

Slack incoming webhooks take a **plain JSON** body (``{"text": ...}``) with no
signature. We therefore use the net-new ``post_unsigned_webhook`` helper (not the
signed ``deliver_webhook``, which HMAC-signs and demands a secret). The body is
the already-redacted :class:`AlertPayload` text, so no raw exploit payload is
ever sent. Returns the ``WebhookDeliveryResult`` so the caller can log the
outcome; never raises.
"""

from __future__ import annotations

import httpx

from src.common.application.helpers.webhooks.delivery import WebhookDeliveryResult
from src.common.application.helpers.webhooks.unsigned import post_unsigned_webhook
from src.scans.infrastructure.alerts.render import AlertPayload


async def post_slack_alert(
    *,
    webhook_url: str,
    payload: AlertPayload,
    client: httpx.AsyncClient | None = None,
) -> WebhookDeliveryResult:
    """POST a redacted alert to a Slack incoming webhook as plain ``{"text": ...}``."""
    return await post_unsigned_webhook(
        url=webhook_url,
        json={"text": payload.as_text()},
        client=client,
    )
