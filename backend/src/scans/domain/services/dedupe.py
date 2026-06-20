"""Finding deduplication service (06-data-model §3.3 / §4).

``dedupe_key = sha256(site_id | source | category | normalize(affected_url) |
param | tool)`` — the stable identity of a finding across scans, which makes
temporal monitoring computable. Computed in Python at parse time, before the DB.
Deduplication by ``dedupe_key`` happens **before** any penalty is computed.
"""

from __future__ import annotations

import hashlib
from urllib.parse import urlparse, urlunparse
from uuid import UUID

_SEP = "|"


def normalize_url(affected_url: str | None) -> str:
    """Collapse cosmetic URL variations that point at the same resource.

    Lowercases scheme+host, strips the default port, drops query and fragment,
    and removes a trailing slash from the path. Returns ``""`` for a missing URL.
    """
    if not affected_url:
        return ""
    raw = affected_url.strip()
    parsed = urlparse(raw if "//" in raw else f"//{raw}")
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()
    if parsed.port and not (
        (scheme == "http" and parsed.port == 80)
        or (scheme == "https" and parsed.port == 443)
    ):
        host = f"{host}:{parsed.port}"
    path = parsed.path or ""
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((scheme, host, path, "", "", ""))


def compute_dedupe_key(
    *,
    site_id: UUID | str,
    source: str,
    category: str,
    affected_url: str | None,
    param: str | None,
    tool: str,
) -> str:
    """Return the 64-char hex sha256 dedupe key for a finding (spec §3.3)."""
    parts = [
        str(site_id),
        source or "",
        category or "",
        normalize_url(affected_url),
        param or "",
        tool or "",
    ]
    digest = hashlib.sha256(_SEP.join(parts).encode("utf-8"))
    return digest.hexdigest()
