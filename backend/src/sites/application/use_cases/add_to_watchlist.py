"""``AddToWatchlist`` — ``POST /watchlist {url, monitor}`` (12-api §"Watchlist").

Resolves (or creates) the site for ``url`` and adds it to the caller's watchlist,
returning the created row (including its ``uuid``) so the client can later
``PATCH``/``DELETE`` it by row id. ``add`` is an idempotent upsert: re-adding the
same site updates ``monitor`` rather than duplicating.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.sites.domain.models.watchlist import WatchlistEntry
from src.sites.domain.repositories.site import SiteRepository
from src.sites.domain.repositories.watchlist import WatchlistRepository


@dataclass
class AddToWatchlist(UseCase):
    user_id: UUID
    url: str
    monitor: bool
    site_repository: SiteRepository
    watchlist_repository: WatchlistRepository

    async def execute(self, *args, **kwargs) -> WatchlistEntry:
        site = await self.site_repository.get_or_create(
            self.url, owner_user_id=self.user_id
        )
        return await self.watchlist_repository.add(
            self.user_id, site.uuid, monitor=self.monitor
        )
