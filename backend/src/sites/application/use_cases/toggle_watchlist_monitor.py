"""``ToggleWatchlistMonitor`` — ``PATCH /watchlist/{id} {monitor}`` (12-api).

Flips the ``monitor`` flag (periodic re-scan) on an existing watchlist row. The
row is resolved and ownership-checked by ``require_watchlist_owner`` upstream;
this use case re-upserts via ``add`` (idempotent on ``(user_id, site_id)``) to set
the new ``monitor`` value and returns the updated row enriched with the site host
+ latest-scan grades (same shape as list/add).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.scans.domain.repositories.scan import ScanRepository
from src.sites.application.services.watchlist_row import (
    WatchlistRowView,
    build_watchlist_row,
)
from src.sites.domain.repositories.site import SiteRepository
from src.sites.domain.repositories.watchlist import WatchlistRepository


@dataclass
class ToggleWatchlistMonitor(UseCase):
    user_id: UUID
    site_id: UUID
    monitor: bool
    watchlist_repository: WatchlistRepository
    site_repository: SiteRepository
    scan_repository: ScanRepository

    async def execute(self, *args, **kwargs) -> WatchlistRowView:
        entry = await self.watchlist_repository.add(
            self.user_id, self.site_id, monitor=self.monitor
        )
        return await build_watchlist_row(
            entry,
            site_repository=self.site_repository,
            scan_repository=self.scan_repository,
        )
