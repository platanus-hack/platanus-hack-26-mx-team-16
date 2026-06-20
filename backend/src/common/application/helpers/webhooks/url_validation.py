"""SSRF guard for outbound webhook URLs (spec §6 / §8 Fase 4).

Validated both when the config is saved (request schema) and before sending
(dispatch activity). Only ``https`` public endpoints are allowed; literal
private / loopback / link-local / reserved IPs and ``localhost`` are rejected.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse


class InvalidWebhookUrlError(ValueError):
    """Raised when a webhook URL is not a safe public https endpoint."""


def validate_webhook_url(url: str) -> str:
    """Return ``url`` if it is a safe https endpoint, else raise ``ValueError``."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        msg = "Webhook URL must use https"
        raise InvalidWebhookUrlError(msg)

    host = parsed.hostname
    if not host:
        msg = "Webhook URL must include a host"
        raise InvalidWebhookUrlError(msg)
    if host == "localhost":
        msg = "Webhook URL cannot point to localhost"
        raise InvalidWebhookUrlError(msg)

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved):
        msg = "Webhook URL cannot point to a private/reserved IP"
        raise InvalidWebhookUrlError(msg)

    return url
