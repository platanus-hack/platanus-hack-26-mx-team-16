"""``ToggleWatchlistMonitor`` — ``PATCH /watchlist/{id} {monitor}`` (12-api).

Flips the ``monitor`` flag (periodic re-scan) on an existing watchlist row. The
row is resolved and ownership-checked by ``require_watchlist_owner`` upstream;
this use case re-upserts via ``add`` (idempotent on ``(user_id, site_id)``) to set
the new ``monitor`` value and returns the updated row.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.sites.domain.models.watchlist import WatchlistEntry
from src.sites.domain.repositories.watchlist import WatchlistRepository


@dataclass
class ToggleWatchlistMonitor(UseCase):
    user_id: UUID
    site_id: UUID
    monitor: bool
    watchlist_repository: WatchlistRepository

    async def execute(self, *args, **kwargs) -> WatchlistEntry:
        return await self.watchlist_repository.add(
            self.user_id, self.site_id, monitor=self.monitor
        )
