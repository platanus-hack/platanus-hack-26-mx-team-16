"""Authenticate an inbound ingest call against its Source (F8 · D3).

``api_key``: constant-time compare of the presented ``dxk_`` key against the
stored hash (reuses F0 ``verify_token``). ``hmac``: recompute ``v1,<base64 HMAC>``
over ``timestamp.body`` and compare, with a timestamp window to defeat replay.
"""

from __future__ import annotations

import base64
import hashlib
import hmac

from src.common.application.helpers.secrets import verify_token
from src.common.domain.enums.sources import SourceAuthMode
from src.connections.domain.models.workflow_source import WorkflowSource

DEFAULT_MAX_SKEW_SECONDS = 300


def compute_source_signature(secret: str, timestamp: int, body: str) -> str:
    """``v1,<base64(HMAC_SHA256(key, "<timestamp>.<body>"))>`` (Svix-style)."""
    key = base64.b64decode(secret.removeprefix("whsec_"))
    digest = hmac.new(key, f"{timestamp}.{body}".encode(), hashlib.sha256).digest()
    return f"v1,{base64.b64encode(digest).decode('ascii')}"


def verify_source_auth(
    source: WorkflowSource,
    *,
    api_key: str | None = None,
    signature: str | None = None,
    timestamp: int | None = None,
    body: str | None = None,
    now: int | None = None,
    max_skew_seconds: int = DEFAULT_MAX_SKEW_SECONDS,
) -> bool:
    if not source.enabled or not source.secret:
        return False

    if source.auth_mode == SourceAuthMode.API_KEY:
        return bool(api_key) and verify_token(api_key, source.secret)

    # HMAC
    if not signature or timestamp is None or body is None:
        return False
    if now is not None and abs(now - timestamp) > max_skew_seconds:
        return False  # anti-replay
    expected = compute_source_signature(source.secret, timestamp, body)
    return hmac.compare_digest(expected, signature)
