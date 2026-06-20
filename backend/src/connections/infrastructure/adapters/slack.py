"""Slack provider adapters (F12 scaffold).

Slack acts as a delivery Destination (posting result messages to a channel). The
external OAuth flow is pending; once connected, delivery will also depend on the
``document.received`` event type (F12 Slack §2a).
"""

from __future__ import annotations

from src.common.domain.models.webhook_destination import WebhookDestination


class SlackDestinationAdapter:
    """Posts result payloads to a Slack channel (F12 · pending)."""

    async def deliver(self, destination: WebhookDestination, payload: dict) -> dict:
        raise NotImplementedError(
            "F12: OAuth/credential flow pending — external. "
            "SlackDestinationAdapter.deliver requires a connected Slack workspace."
        )
