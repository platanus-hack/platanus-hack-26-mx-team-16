"""Signed webhook delivery over ``httpx`` with bounded per-POST retry.

See ``product/specs/source-webhooks/standard-webhooks.md`` §4.7 / §4.8 and decisión §5.23 (3 attempts,
exponential backoff ~1s/2s/4s). This helper never raises: it always returns a
:class:`WebhookDeliveryResult` so callers can record the outcome and keep the
run fire-and-forget (decisión §5.16).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx

from src.common.application.helpers.webhooks.signing import (
    build_signature_headers,
    sign_payload,
)

DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_ATTEMPTS = 3  # decisión §5.23 (per-POST immediate retries)
_BACKOFF_BASE_SECONDS = 1.0


@dataclass(slots=True)
class WebhookDeliveryResult:
    """Outcome of a (possibly retried) webhook delivery."""

    delivered: bool
    attempts: int
    status_code: int | None = None
    error: str | None = None


_HTTP_OK_MIN = 200
_HTTP_OK_MAX = 300
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_SERVER_ERROR_MIN = 500


def _is_retryable(status_code: int) -> bool:
    """5xx and 429 are retried; other 4xx are terminal (§4.8)."""
    return status_code >= _HTTP_SERVER_ERROR_MIN or status_code == _HTTP_TOO_MANY_REQUESTS


async def deliver_webhook(
    *,
    url: str,
    body: str,
    secret: str,
    event_id: str,
    timestamp: int,
    client: httpx.AsyncClient | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> WebhookDeliveryResult:
    """POST a signed webhook with bounded exponential backoff.

    2xx → ``delivered``. 5xx / timeout / 429 → retried up to ``max_attempts``.
    Other 4xx → terminal failure (no retry). ``body`` is sent verbatim so the
    signature matches the received bytes.
    """
    signature = sign_payload(secret, body, event_id, timestamp)
    headers = build_signature_headers(event_id=event_id, timestamp=timestamp, signature=signature)

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=timeout_seconds)
    last_status: int | None = None
    last_error: str | None = None
    try:
        for attempt in range(1, max_attempts + 1):
            try:
                response = await client.post(url, content=body, headers=headers)
                last_status = response.status_code
                if _HTTP_OK_MIN <= response.status_code < _HTTP_OK_MAX:
                    return WebhookDeliveryResult(delivered=True, attempts=attempt, status_code=response.status_code)
                if not _is_retryable(response.status_code):
                    return WebhookDeliveryResult(
                        delivered=False,
                        attempts=attempt,
                        status_code=response.status_code,
                        error=f"HTTP {response.status_code}",
                    )
                last_error = f"HTTP {response.status_code}"
            except httpx.HTTPError as exc:
                last_error = str(exc)
            if attempt < max_attempts:
                await asyncio.sleep(_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
        return WebhookDeliveryResult(
            delivered=False,
            attempts=max_attempts,
            status_code=last_status,
            error=last_error,
        )
    finally:
        if owns_client:
            await client.aclose()
