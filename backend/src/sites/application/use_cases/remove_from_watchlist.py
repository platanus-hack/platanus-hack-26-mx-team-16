"""``RemoveFromWatchlist`` — ``DELETE /watchlist/{id}`` (12-api §"Watchlist").

The ``{id}`` is a watchlist-row uuid; ``require_watchlist_owner`` resolves it to
the owned row (404 otherwise) and hands us its ``site_id``. The repo removes by
``(user_id, site_id)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.sites.domain.repositories.watchlist import WatchlistRepository


@dataclass
class RemoveFromWatchlist(UseCase):
    user_id: UUID
    site_id: UUID
    watchlist_repository: WatchlistRepository

    async def execute(self, *args, **kwargs) -> None:
        await self.watchlist_repository.remove(self.user_id, self.site_id)
