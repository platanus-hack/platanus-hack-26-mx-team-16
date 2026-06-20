"""Canonical host classification — single source of truth (spec §2.4, §3).

``is_gov`` drives the public ``.gob.mx`` leaderboard (08), the reinforced
(non-blocking) warning copy for sensitive hosts (13, §2.4) and the default
visibility of a scan (``levels.default_visibility``, §2.3). It is computed
server-side at insert time, **never** accepted from the client.

This module is THE source of truth: ``src.sites.domain.services.host`` delegates
here so there is exactly one ``is_gov`` implementation in the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

# ``.gob.mx`` suffix (and the bare apex ``gob.mx``) marks a Mexican government
# site. Case-insensitive; port/trailing-dot tolerant (see ``normalize_hostname``).
GOV_SUFFIX = ".gob.mx"

# Additional suffixes treated as "sensitive" beyond gov — they only reinforce the
# warning copy and default visibility (§2.4), they NEVER block a scan. ``is_gov``
# is always a subset of ``is_sensitive``. Kept small and explicit on purpose.
SENSITIVE_SUFFIXES: tuple[str, ...] = (
    ".mil.mx",  # military
)


@dataclass(frozen=True)
class HostFlags:
    """Server-derived host attributes for a ``sites`` row.

    ``is_sensitive`` is a superset of ``is_gov`` (every gov host is sensitive).
    """

    hostname: str
    is_gov: bool
    is_sensitive: bool


def normalize_hostname(value: str) -> str:
    """Lowercase, strip a trailing dot and any ``:port``. Best-effort."""
    host = value.strip().lower()
    # Drop port if present.
    if ":" in host:
        host = host.split(":", 1)[0]
    # Drop a single trailing dot (FQDN root).
    if host.endswith("."):
        host = host[:-1]
    return host


def _extract_hostname(url: str) -> str:
    """Parse ``url`` (bare hostname or full URL) into a normalized hostname."""
    raw = url.strip()
    parsed = urlparse(raw if "//" in raw else f"//{raw}")
    return normalize_hostname(parsed.hostname or parsed.path or raw)


def is_gov_hostname(hostname: str) -> bool:
    """True only for the ``.gob.mx`` suffix (or the bare apex ``gob.mx``).

    Accepts either an already-normalized hostname or a raw value; normalization
    (lowercase, port/trailing-dot stripping) is applied defensively.
    """
    host = normalize_hostname(hostname)
    return host == "gob.mx" or host.endswith(GOV_SUFFIX)


def is_sensitive_hostname(hostname: str) -> bool:
    """``is_gov`` ∪ other suffixes marked sensitive → reinforced copy (§2.4).

    Non-blocking: this flag only affects warning copy (13) and default
    visibility (§2.3); it never prevents launching an active scan.
    """
    host = normalize_hostname(hostname)
    if is_gov_hostname(host):
        return True
    return any(host.endswith(suffix) for suffix in SENSITIVE_SUFFIXES)


def resolve_host_flags(url: str) -> HostFlags:
    """Parse ``url`` into a normalized hostname and derive its legal flags.

    Accepts a bare hostname or a full URL. ``is_gov`` is true only for the
    ``.gob.mx`` suffix (case-insensitive, port/trailing-dot tolerant); 06 uses
    this to populate ``sites.is_gov``.
    """
    host = _extract_hostname(url)
    return HostFlags(
        hostname=host,
        is_gov=is_gov_hostname(host),
        is_sensitive=is_sensitive_hostname(host),
    )
