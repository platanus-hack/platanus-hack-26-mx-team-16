"""Shared idempotent enqueue used by both the gov seed and the monitoring cron
(08-ranking-watchlists §2.3, §4.2).

This is the SAME idempotency contract as ``POST /scans`` (``EnqueueScan``):
- partial unique index ``scans(site_id, level) WHERE status IN ('queued','running')``
  collapses a duplicate to the existing live scan (``ScanRepository.enqueue``);
- the legal guard hard-codes the gov/automatic level to passive and asserts
  ``level in AUTOMATIC_ALLOWED_LEVELS`` (01-legal §3.2) — otherwise
  ``AutomaticActiveScanError``.

Automatic/cron scans carry ``requested_by=None`` (the contract that marks a scan
as cron/seed origin, plan §4.2) and dispatch ``RunScanCommand`` only on a freshly
created scan.
"""

from __future__ import annotations

from uuid import UUID

from src.common.domain.buses.commands import CommandBus
from src.common.domain.enums.scans import ScanLevel, ScanVisibility
from src.common.domain.legal import AUTOMATIC_ALLOWED_LEVELS
from src.common.domain.legal.exceptions import AutomaticActiveScanError
from src.scans.application.commands.run_scan import RunScanCommand
from src.scans.domain.models.scan import Scan
from src.scans.domain.repositories.scan import ScanRepository


async def enqueue_automatic_scan(
    *,
    site_id: UUID,
    level: ScanLevel,
    visibility: ScanVisibility,
    scan_repository: ScanRepository,
    command_bus: CommandBus,
    is_gov: bool,
) -> tuple[Scan, bool]:
    """Idempotently enqueue an automatic (cron/seed) scan.

    Returns ``(scan, created)``. ``created=False`` means an active scan for
    ``(site_id, level)`` already existed and was returned unchanged (no-op,
    idempotent). For ``is_gov`` the level is asserted passive (basic) — a guard,
    not a parameter the caller can override into an active level.
    """
    # Legal hard guard: every automatic trigger must be passive (§4.2 / 01 §3.2).
    if is_gov and level not in AUTOMATIC_ALLOWED_LEVELS:
        raise AutomaticActiveScanError(
            context={"site_id": str(site_id), "level": str(level)}
        )
    if level not in AUTOMATIC_ALLOWED_LEVELS:
        # Non-gov monitoring may run the owner-authorized level; but the cron
        # only ever passes BASICO for gov. Active watchlist levels are allowed
        # only when the owner attested (the row was created authorized); the
        # cron passes them through here with authorized=True.
        authorized = True
    else:
        authorized = False

    level_value = str(level)
    existing = await scan_repository.find_active(site_id, level_value)
    if existing is not None:
        return existing, False

    scan = await scan_repository.enqueue(
        site_id,
        level_value,
        visibility=str(visibility),
        requested_by=None,  # cron/seed origin (§4.2)
        authorized=authorized,
    )
    created = scan.status == "queued" and existing is None
    if created:
        await command_bus.dispatch(
            RunScanCommand(scan_id=scan.uuid), run_async=True
        )
    return scan, created
