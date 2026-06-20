"""Email is a PUSH channel as of E6 (W5) — not a polled Source.

The F12 ``EmailSourceAdapter.poll`` scaffold is gone: inbound mail now arrives
via ``POST /v1/channels/email/{token}`` and is parsed by the provider-agnostic
:class:`~src.connections.domain.channels.base.ChannelAdapter` implementations in
``src/connections/infrastructure/channels/`` (mailpit dev, mailgun, …). This
module is kept as a breadcrumb to those adapters.
"""

from __future__ import annotations

from src.connections.infrastructure.channels.email_mailgun import MailgunChannelAdapter
from src.connections.infrastructure.channels.email_mailpit import MailpitChannelAdapter

__all__ = ["MailgunChannelAdapter", "MailpitChannelAdapter"]
