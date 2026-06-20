"""``SiteRepository`` ABC (06-data-model §1, plan §2.3)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.sites.domain.models.site import Site


class SiteRepository(ABC):
    @abstractmethod
    async def find(self, site_id: UUID) -> Site | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_hostname(self, hostname: str) -> Site | None:
        raise NotImplementedError

    @abstractmethod
    async def get_or_create(
        self, url: str, *, owner_user_id: UUID | None = None, country: str | None = None
    ) -> Site:
        """Resolve the site for ``url`` (one row per hostname), creating it if
        absent. ``is_gov`` is derived server-side via ``resolve_host_flags`` and
        never taken from the caller (spec §3.1)."""
        raise NotImplementedError

    @abstractmethod
    async def set_latest_scan(self, site_id: UUID, scan_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_gov(self) -> list[Site]:
        """Sites where ``is_gov`` is true (global leaderboard subjects)."""
        raise NotImplementedError
