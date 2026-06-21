"""``ListWatchlist`` — ``GET /watchlist`` (12-api §"Watchlist").

Returns enriched rows (site host + latest-scan grades), not bare entries, so the
watchlist UI can render each domain's grades in one round-trip.
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
class ListWatchlist(UseCase):
    user_id: UUID
    watchlist_repository: WatchlistRepository
    site_repository: SiteRepository
    scan_repository: ScanRepository

    async def execute(self, *args, **kwargs) -> list[WatchlistRowView]:
        entries = await self.watchlist_repository.list_for_user(self.user_id)
        return [
            await build_watchlist_row(
                entry,
                site_repository=self.site_repository,
                scan_repository=self.scan_repository,
            )
            for entry in entries
        ]
