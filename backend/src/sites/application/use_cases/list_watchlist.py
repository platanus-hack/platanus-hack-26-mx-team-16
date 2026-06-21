"""``ListWatchlist`` — ``GET /watchlist`` (12-api §"Watchlist")."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.sites.domain.models.watchlist import WatchlistEntry
from src.sites.domain.repositories.watchlist import WatchlistRepository


@dataclass
class ListWatchlist(UseCase):
    user_id: UUID
    watchlist_repository: WatchlistRepository

    async def execute(self, *args, **kwargs) -> list[WatchlistEntry]:
        return await self.watchlist_repository.list_for_user(self.user_id)
