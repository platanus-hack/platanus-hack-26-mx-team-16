"""Attestation gate — the pure check behind ``POST /scans`` (spec §2.1).

The ``enqueue_scan`` use case (12) calls ``enforce_attestation`` **before**
touching the queue. The checkbox is recorded consent, never the only barrier —
the real barriers live in the scheduler (§2.2), ranking visibility (§2.3) and
the worker whitelist (§3). This gate only guarantees: an active level is never
enqueued without an explicit ``authorized=true``.
"""

from __future__ import annotations

from src.common.domain.enums.scans import ScanLevel
from src.common.domain.legal.exceptions import AttestationRequiredError
from src.common.domain.legal.levels import is_active


def enforce_attestation(*, level: ScanLevel, authorized: bool) -> None:
    """Raise ``AttestationRequiredError`` if an active scan lacks attestation.

    Passive scans (basic) never require attestation and pass through. The check
    is pure and has no side effects — persisting ``authorized``/``authorized_at``/
    ``requested_by`` is the caller's (12) responsibility.
    """
    if is_active(level) and not authorized:
        raise AttestationRequiredError(context={"level": str(level)})
