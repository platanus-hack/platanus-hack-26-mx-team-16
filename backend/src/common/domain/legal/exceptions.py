"""Legal/ethics domain errors (spec §2.1, §2.2).

Both extend ``DomainError`` (code, message, status_code) so the existing API
error handler translates them to the right HTTP status automatically.
"""

from __future__ import annotations

from typing import Any

from src.common.domain.exceptions._base import DomainError


class AttestationRequiredError(DomainError):
    """An active scan was requested without ``authorized=true`` (§2.1).

    Surfaced by ``POST /scans`` as ``422`` (12-api). Without attestation the
    active job is **not** enqueued.
    """

    def __init__(self, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="attestation_required",
            message=(
                "An active (intrusive) scan requires explicit authorization. "
                "You must attest that you are authorized to audit this domain."
            ),
            status_code=422,
            context=context,
        )


class AutomaticActiveScanError(DomainError):
    """A non-passive level reached an automatic trigger path (§2.2).

    This is a **server-side invariant guard** for the scheduler/seed-cron, never
    a user-facing input error: every automatic trigger must be passive. Reaching
    it means the scheduler tried to emit ``level not in AUTOMATIC_ALLOWED_LEVELS``
    — a bug — so it surfaces as ``500``.
    """

    def __init__(self, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="automatic_active_forbidden",
            message=(
                "Automatic scans must be passive: the scheduler may only emit "
                "the basic level. This is a code invariant, not a configuration."
            ),
            status_code=500,
            context=context,
        )
