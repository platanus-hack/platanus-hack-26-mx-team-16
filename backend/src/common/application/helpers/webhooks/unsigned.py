"""Unsigned (plain JSON) webhook POST for Slack incoming webhooks.

A Slack *incoming webhook* expects a plain JSON body (``{"text": ...}``) with
**no** signature headers, secret, or ``event_id``/``timestamp`` — unlike the
signed standard-webhooks emitter in ``delivery.py`` (which is for our own
outbound webhooks and HMAC-signs every payload). Reusing ``deliver_webhook``
here would attach signature headers Slack ignores and demand a ``secret`` that
does not exist for an incoming webhook, so this is a net-new, deliberately
minimal helper.

Like ``deliver_webhook`` it **never raises**: it always returns a
:class:`WebhookDeliveryResult` so the monitoring/alert path stays
fire-and-forget (08-ranking-watchlists §5.1).
"""

from __future__ import annotations

from typing import Any

import httpx

from src.common.application.helpers.webhooks.delivery import WebhookDeliveryResult

DEFAULT_TIMEOUT_SECONDS = 10.0

_HTTP_OK_MIN = 200
_HTTP_OK_MAX = 300


async def post_unsigned_webhook(
    *,
    url: str,
    json: dict[str, Any],
    client: httpx.AsyncClient | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> WebhookDeliveryResult:
    """POST a plain JSON body to ``url`` (e.g. a Slack incoming webhook).

    2xx → ``delivered=True``. Any non-2xx status or transport error →
    ``delivered=False`` with the captured ``status_code``/``error``. Never
    raises — the caller records the outcome and moves on.
    """
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=timeout_seconds)
    try:
        try:
            response = await client.post(url, json=json)
        except httpx.HTTPError as exc:
            return WebhookDeliveryResult(
                delivered=False, attempts=1, status_code=None, error=str(exc)
            )
        delivered = _HTTP_OK_MIN <= response.status_code < _HTTP_OK_MAX
        return WebhookDeliveryResult(
            delivered=delivered,
            attempts=1,
            status_code=response.status_code,
            error=None if delivered else f"HTTP {response.status_code}",
        )
    finally:
        if owns_client:
            await client.aclose()
