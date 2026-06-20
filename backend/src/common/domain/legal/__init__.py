"""Owliver legal/ethics invariant — single source of truth (feature 01).

This package centralizes the legal/ethics invariants of the pentest platform so
the rule never gets scattered or allowed to diverge across the worker (04), the
scheduler/ranking (08), the API (12) and the frontend (13). It is **dependency-
free** (no I/O, no infrastructure imports) so any layer — use case, worker or
scheduler — can import it without cycles.

The four code-enforced controls plus rate-limit/UA are exposed here as pure
predicates and frozen contracts:

- ``constants``         — identifiable User-Agent + the two distinct rate limits.
- ``host``              — canonical ``is_gov``/``is_sensitive`` classification.
- ``levels``            — active/passive predicates + default visibility + the
                          frozen set of levels the scheduler may auto-emit.
- ``passive_profile``   — the legal allow-list contract of the gov passive scan.
- ``attestation_gate``  — the pure attestation check (active ⇒ authorized).
- ``exceptions``        — ``AttestationRequiredError`` (422) /
                          ``AutomaticActiveScanError`` (500).
- ``robots``            — the ``RobotsPolicy`` Protocol (contract; impl in 04).
"""

from src.common.domain.legal.attestation_gate import enforce_attestation
from src.common.domain.legal.constants import (
    API_SCAN_RATE_LIMIT,
    SCANNER_USER_AGENT,
    WORKER_NUCLEI_RATE,
    WORKER_REQUEST_DELAY_MS,
)
from src.common.domain.legal.exceptions import (
    AttestationRequiredError,
    AutomaticActiveScanError,
)
from src.common.domain.legal.host import (
    HostFlags,
    is_gov_hostname,
    is_sensitive_hostname,
    normalize_hostname,
    resolve_host_flags,
)
from src.common.domain.legal.levels import (
    AUTOMATIC_ALLOWED_LEVELS,
    default_visibility,
    is_active,
)
from src.common.domain.legal.passive_profile import (
    GOV_PASSIVE_PROFILE,
    PassiveProfile,
    ToolInvocation,
    assert_within_passive_profile,
)
from src.common.domain.legal.robots import RobotsPolicy

__all__ = [
    # constants
    "SCANNER_USER_AGENT",
    "API_SCAN_RATE_LIMIT",
    "WORKER_NUCLEI_RATE",
    "WORKER_REQUEST_DELAY_MS",
    # host
    "HostFlags",
    "is_gov_hostname",
    "is_sensitive_hostname",
    "normalize_hostname",
    "resolve_host_flags",
    # levels
    "AUTOMATIC_ALLOWED_LEVELS",
    "is_active",
    "default_visibility",
    # passive profile
    "GOV_PASSIVE_PROFILE",
    "PassiveProfile",
    "ToolInvocation",
    "assert_within_passive_profile",
    # attestation gate
    "enforce_attestation",
    # exceptions
    "AttestationRequiredError",
    "AutomaticActiveScanError",
    # robots
    "RobotsPolicy",
]
