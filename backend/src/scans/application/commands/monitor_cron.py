"""``MonitorCronHandler`` — the body of the SAQ ``CronJob``
(08-ranking-watchlists §4.1/§4.2).

On each tick it re-enqueues, idempotently:
1. ``watchlist.monitor=true`` sites — at the owner-authorized level;
2. gov seed sites (``is_gov``) — **always** basic/passive.

Each enqueue goes through ``enqueue_automatic_scan`` (the SAME idempotency as
``POST /scans``: partial unique index + return-the-live-scan), so a still-running
scan from the previous cycle is a no-op. Gov levels are hard-guarded to
``ScanLevel.BASICO`` (``AutomaticActiveScanError`` otherwise). The cron only
**enqueues**; alert evaluation happens at the end of each scan
(``EvaluateSiteAlerts``), not here.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.application.logging import get_logger
from src.common.domain.buses.commands import CommandBus
from src.common.domain.enums.scans import ScanLevel, ScanVisibility
from src.scans.application.commands.enqueue_monitor_scan import enqueue_automatic_scan
from src.scans.domain.repositories.scan import ScanRepository
from src.sites.domain.repositories.site import SiteRepository
from src.sites.domain.repositories.watchlist import WatchlistRepository

logger = get_logger(__name__)


@dataclass
class MonitorCronHandler:
    site_repository: SiteRepository
    watchlist_repository: WatchlistRepository
    scan_repository: ScanRepository
    command_bus: CommandBus
    monitor_level_default: ScanLevel = ScanLevel.BASICO

    async def execute(self) -> int:
        """Re-enqueue every monitored site. Returns the count of newly-created
        scans (idempotent hits are not counted)."""
        seen: set[UUID] = set()
        created_count = 0

        # 1. Watchlist sites with monitor=true → owner-authorized level.
        for entry in await self.watchlist_repository.sites_with_monitor_true():
            if entry.site_id in seen:
                continue
            seen.add(entry.site_id)
            site = await self.site_repository.find(entry.site_id)
            if site is None:
                continue
            # Gov sites are always passive even if monitored; non-gov watchlist
            # sites use the configured monitoring level (passive by default).
            level = (
                ScanLevel.BASICO if site.is_gov else self.monitor_level_default
            )
            _, created = await enqueue_automatic_scan(
                site_id=site.uuid,
                level=level,
                visibility=(
                    ScanVisibility.PUBLIC if site.is_gov else ScanVisibility.PRIVATE
                ),
                scan_repository=self.scan_repository,
                command_bus=self.command_bus,
                is_gov=site.is_gov,
            )
            if created:
                created_count += 1

        # 2. Gov seed sites → always basic/passive.
        for site in await self.site_repository.list_gov():
            if site.uuid in seen:
                continue
            seen.add(site.uuid)
            _, created = await enqueue_automatic_scan(
                site_id=site.uuid,
                level=ScanLevel.BASICO,
                visibility=ScanVisibility.PUBLIC,
                scan_repository=self.scan_repository,
                command_bus=self.command_bus,
                is_gov=True,
            )
            if created:
                created_count += 1

        logger.info("monitor_cron.completed", scans_enqueued=created_count)
        return created_count
