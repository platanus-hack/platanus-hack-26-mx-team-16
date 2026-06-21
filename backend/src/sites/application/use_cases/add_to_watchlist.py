"""``AddToWatchlist`` — ``POST /watchlist {url, monitor}`` (12-api §"Watchlist").

Resolves (or creates) the site for ``url`` and adds it to the caller's watchlist,
returning the created row enriched with the site host + latest-scan grades (the
same shape the list endpoint returns) so the client can render it immediately and
later ``PATCH``/``DELETE`` it by row id. ``add`` is an idempotent upsert: re-adding
the same site updates ``monitor`` rather than duplicating.
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
class AddToWatchlist(UseCase):
    user_id: UUID
    url: str
    monitor: bool
    site_repository: SiteRepository
    watchlist_repository: WatchlistRepository
    scan_repository: ScanRepository

    async def execute(self, *args, **kwargs) -> WatchlistRowView:
        site = await self.site_repository.get_or_create(
            self.url, owner_user_id=self.user_id
        )
        entry = await self.watchlist_repository.add(
            self.user_id, site.uuid, monitor=self.monitor
        )
        return await build_watchlist_row(
            entry,
            site=site,
            site_repository=self.site_repository,
            scan_repository=self.scan_repository,
        )
