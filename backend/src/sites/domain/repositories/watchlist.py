"""``WatchlistRepository`` ABC (06-data-model §3.6)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.sites.domain.models.watchlist import WatchlistEntry


class WatchlistRepository(ABC):
    @abstractmethod
    async def add(
        self, user_id: UUID, site_id: UUID, *, monitor: bool = True
    ) -> WatchlistEntry:
        raise NotImplementedError

    @abstractmethod
    async def remove(self, user_id: UUID, site_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_for_user(self, user_id: UUID) -> list[WatchlistEntry]:
        raise NotImplementedError

    @abstractmethod
    async def find(self, user_id: UUID, site_id: UUID) -> WatchlistEntry | None:
        raise NotImplementedError

    @abstractmethod
    async def sites_with_monitor_true(self) -> list[WatchlistEntry]:
        """All watchlist rows with ``monitor=true`` across every user — the
        single signal that gates a site into the re-scan cron
        (08-ranking-watchlists §4.1)."""
        raise NotImplementedError
