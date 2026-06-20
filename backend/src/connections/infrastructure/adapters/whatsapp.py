"""WhatsApp is a PUSH channel as of E6 (W5) — not a polled Source.

The F12 ``WhatsappSourceAdapter.poll`` scaffold is gone: inbound messages now
arrive via ``POST /v1/channels/whatsapp/{token}`` (with the Meta
``GET hub.challenge`` handshake) and are parsed by
:class:`~src.connections.infrastructure.channels.whatsapp_cloud.WhatsappCloudChannelAdapter`.
This module is kept as a breadcrumb to that adapter.
"""

from __future__ import annotations

from src.connections.infrastructure.channels.whatsapp_cloud import WhatsappCloudChannelAdapter

__all__ = ["WhatsappCloudChannelAdapter"]
