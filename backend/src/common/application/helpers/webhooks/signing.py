"""HMAC-SHA256 signing for outbound webhooks (Svix-style).

See ``product/specs/source-webhooks/standard-webhooks.md`` §4.7 and decisions §5.6 / §5.17:

- ``signed_content = f"{event_id}.{timestamp}.{body}"`` where ``body`` is the
  exact JSON string that is sent on the wire.
- The signing key is the **base64-decoded** token (the part after the
  ``whsec_`` prefix), so receivers can reuse Svix client libraries verbatim.
- The signature header value is ``v1,<base64(HMAC_SHA256(key, signed_content))>``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac

from src.common.application.helpers.secrets import (
    SECRET_PREFIX_HMAC,
    generate_base64_secret,
)

WEBHOOK_USER_AGENT = "Doxiq-Webhooks/1.0"
SECRET_PREFIX = SECRET_PREFIX_HMAC


def generate_webhook_secret() -> str:
    """Generate a ``whsec_``-prefixed, standard-base64 secret (Svix-style).

    The token after the prefix is standard base64 of 32 random bytes, so
    :func:`sign_payload` can base64-decode it back to the raw HMAC key (§5.17).
    Thin alias over :func:`secrets.generate_base64_secret` (F0 unification).
    """
    return generate_base64_secret(SECRET_PREFIX)


def _decode_secret(secret: str) -> bytes:
    """Return the raw HMAC key from a ``whsec_``-prefixed, base64 secret.

    Svix-strict (decisión §5.17): the token after ``whsec_`` is base64; the
    HMAC key is its decoded bytes.
    """
    token = secret.removeprefix(SECRET_PREFIX)
    return base64.b64decode(token)


def sign_payload(secret: str, body: str, event_id: str, timestamp: int) -> str:
    """Compute the ``Doxiq-Signature`` value for a webhook delivery.

    ``body`` MUST be the exact JSON string that is POSTed, so the receiver can
    recompute the same signature over the bytes it receives.
    """
    signed_content = f"{event_id}.{timestamp}.{body}"
    digest = hmac.new(
        _decode_secret(secret),
        signed_content.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"v1,{base64.b64encode(digest).decode('ascii')}"


def build_signature_headers(*, event_id: str, timestamp: int, signature: str) -> dict[str, str]:
    """Standard outbound headers for a signed webhook POST (§4.7)."""
    return {
        "Content-Type": "application/json",
        "User-Agent": WEBHOOK_USER_AGENT,
        "Doxiq-Id": event_id,
        "Doxiq-Timestamp": str(timestamp),
        "Doxiq-Signature": signature,
    }
