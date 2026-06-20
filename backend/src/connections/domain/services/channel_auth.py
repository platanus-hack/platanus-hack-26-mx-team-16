"""Per-provider channel signature verifiers (E6 · W5 · diseño §5).

These are NOT the Svix-style ``v1,<base64>`` scheme of :mod:`source_auth` (which
authenticates the API ingest endpoint). Native channels are signed by the
provider itself:

- **Meta WhatsApp Cloud**: ``X-Hub-Signature-256: sha256=<hex HMAC_SHA256(app_secret, raw_body)>``
  over the EXACT raw request body.
- **Mailgun Routes**: ``signature = hex HMAC_SHA256(signing_key, "<timestamp><token>")``.

All comparisons are constant-time (:func:`hmac.compare_digest`).
"""

from __future__ import annotations

import hashlib
import hmac
import time

_META_PREFIX = "sha256="

# Mailgun's (timestamp, token, signature) triple is replayable forever unless we
# bound the timestamp; mirror the Svix-style window used by ``verify_source_auth``.
DEFAULT_MAX_SKEW_SECONDS = 300


def verify_meta_signature(app_secret: str, raw_body: bytes, header_value: str | None) -> bool:
    """Verify Meta's ``X-Hub-Signature-256`` over the raw request body."""
    if not app_secret or not header_value:
        return False
    if not header_value.startswith(_META_PREFIX):
        return False
    presented = header_value[len(_META_PREFIX) :]
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, presented)


def verify_mailgun_signature(
    signing_key: str,
    timestamp: str | None,
    token: str | None,
    signature: str | None,
    *,
    now: int | None = None,
    max_skew_seconds: int = DEFAULT_MAX_SKEW_SECONDS,
) -> bool:
    """Verify Mailgun's ``HMAC_SHA256(signing_key, timestamp+token)`` (hex).

    The signature alone is replayable forever (each replay can carry a fresh
    ``Message-Id`` to defeat dedup), so the ``timestamp`` must also be recent:
    reject when it is more than ``max_skew_seconds`` away from ``now``.
    """
    if not signing_key or not timestamp or not token or not signature:
        return False
    try:
        sent_at = int(timestamp)
    except (TypeError, ValueError):
        return False  # non-int timestamp -> reject, not 500
    current = int(time.time()) if now is None else now
    if abs(current - sent_at) > max_skew_seconds:
        return False  # anti-replay
    expected = hmac.new(
        signing_key.encode(), f"{timestamp}{token}".encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
