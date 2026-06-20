"""Level/visibility predicates — the rules that decide automatic & public (spec §2.2, §2.3).

Pure predicates over the frozen ``ScanLevel`` / ``ScanVisibility`` enums (06,
``src.common.domain.enums.scans``). ``legal`` only contributes the **decision**;
the enums themselves are owned by 06.
"""

from __future__ import annotations

from src.common.domain.enums.scans import ScanLevel, ScanVisibility

# §2.2 — the ONLY level the scheduler / seed-cron may auto-emit. Every automatic
# trigger is passive. 08 asserts ``level in AUTOMATIC_ALLOWED_LEVELS`` before
# enqueuing, raising ``AutomaticActiveScanError`` otherwise. Frozen on purpose:
# the scheduler does NOT accept ``level`` as a configurable parameter.
AUTOMATIC_ALLOWED_LEVELS: frozenset[ScanLevel] = frozenset({ScanLevel.BASICO})

# The active levels — intrusive, user-initiated only, behind the attestation gate.
ACTIVE_LEVELS: frozenset[ScanLevel] = frozenset(
    {ScanLevel.INTERMEDIO, ScanLevel.AVANZADO}
)


def is_active(level: ScanLevel) -> bool:
    """True for intrusive levels (intermediate / advanced).

    Active levels require attestation (``attestation_gate.enforce_attestation``)
    and are never auto-emitted by the scheduler.
    """
    return level in ACTIVE_LEVELS


def default_visibility(
    *, is_gov: bool, level: ScanLevel, has_owner: bool
) -> ScanVisibility:
    """Default visibility of a scan at creation time (§2.3).

    Only a gov, passive (basic), un-owned scan is public — that is the automatic
    ``.gob.mx`` leaderboard surface, which is 100% non-intrusive. Everything else
    (any active level, or any scan with an owner) is private to its account; a
    user must explicitly share it (``/r/{token}``) to make it public.
    """
    if is_gov and not has_owner and not is_active(level):
        return ScanVisibility.PUBLIC
    return ScanVisibility.PRIVATE
