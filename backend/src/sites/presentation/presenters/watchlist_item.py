"""Watchlist-item presenter — ``WatchlistEntry`` → camelCase (12-api §"Watchlist").

Exposes the **row uuid** as ``id`` so the client can ``PATCH``/``DELETE`` the entry
by row id (never by site_id), per the spec.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.common.domain.interfaces.presenter import Presenter
from src.sites.domain.models.watchlist import WatchlistEntry


@dataclass
class WatchlistItemPresenter(Presenter[WatchlistEntry]):
    instance: WatchlistEntry

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.instance.uuid),
            "siteId": str(self.instance.site_id),
            "monitor": self.instance.monitor,
            "createdAt": self.instance.created_at,
            "updatedAt": self.instance.updated_at,
        }
