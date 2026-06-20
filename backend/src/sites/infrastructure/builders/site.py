"""ORM -> domain builders for the sites module (06-data-model)."""

from __future__ import annotations

from src.common.database.models.sites.notification_prefs import NotificationPrefsORM
from src.common.database.models.sites.site import SiteORM
from src.common.database.models.sites.watchlist import WatchlistORM
from src.sites.domain.models.notification_prefs import NotificationPrefs
from src.sites.domain.models.site import Site
from src.sites.domain.models.watchlist import WatchlistEntry


def build_site(orm: SiteORM) -> Site:
    return Site.model_validate(orm)


def build_watchlist_entry(orm: WatchlistORM) -> WatchlistEntry:
    return WatchlistEntry.model_validate(orm)


def build_notification_prefs(orm: NotificationPrefsORM) -> NotificationPrefs:
    return NotificationPrefs.model_validate(orm)
