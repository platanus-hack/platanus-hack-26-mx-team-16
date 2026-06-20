"""Host resolution service (06-data-model §3.1).

``is_gov`` is computed here at insert time, **never** accepted from the client:
``is_gov = hostname.endswith('.gob.mx')``. This is the source of the global
``.gob.mx`` leaderboard (08-ranking-watchlists).

The canonical implementation now lives in the dependency-free legal package
(``src.common.domain.legal.host``, feature 01) so there is exactly one ``is_gov``
source of truth across the codebase. This module re-exports it; ``sql_site.py``
keeps importing ``resolve_host_flags`` / ``HostFlags`` from here unchanged.
"""

from __future__ import annotations

from src.common.domain.legal.host import (
    GOV_SUFFIX,
    HostFlags,
    is_gov_hostname,
    is_sensitive_hostname,
    normalize_hostname,
    resolve_host_flags,
)

__all__ = [
    "GOV_SUFFIX",
    "HostFlags",
    "is_gov_hostname",
    "is_sensitive_hostname",
    "normalize_hostname",
    "resolve_host_flags",
]
