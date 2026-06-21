"""Unit tests for watchlist + alert-prefs use cases (12-api). DB-less."""

from unittest.mock import AsyncMock
from uuid import uuid4

from expects import be_false, be_true, equal, expect

from src.sites.application.use_cases.add_to_watchlist import AddToWatchlist
from src.sites.application.use_cases.get_alert_prefs import GetAlertPrefs
from src.sites.application.use_cases.remove_from_watchlist import RemoveFromWatchlist
from src.sites.application.use_cases.toggle_watchlist_monitor import (
    ToggleWatchlistMonitor,
)
from src.sites.application.use_cases.update_alert_prefs import UpdateAlertPrefs
from src.sites.domain.models.notification_prefs import NotificationPrefs
from src.sites.domain.models.site import Site
from src.sites.domain.models.watchlist import WatchlistEntry


def _site() -> Site:
    return Site(uuid=uuid4(), url="https://x.com", hostname="x.com", is_gov=False)


def _entry(user_id, site_id, monitor=True) -> WatchlistEntry:
    return WatchlistEntry(uuid=uuid4(), user_id=user_id, site_id=site_id, monitor=monitor)


async def test_add_to_watchlist_resolves_site_and_returns_row():
    user_id = uuid4()
    site = _site()
    site_repo = AsyncMock()
    site_repo.get_or_create.return_value = site
    wl_repo = AsyncMock()
    entry = _entry(user_id, site.uuid)
    wl_repo.add.return_value = entry

    result = await AddToWatchlist(
        user_id=user_id,
        url="https://x.com",
        monitor=True,
        site_repository=site_repo,
        watchlist_repository=wl_repo,
    ).execute()

    expect(result.uuid).to(equal(entry.uuid))
    _, kwargs = wl_repo.add.call_args
    expect(kwargs["monitor"]).to(be_true)


async def test_toggle_monitor_calls_add_with_new_value():
    user_id, site_id = uuid4(), uuid4()
    wl_repo = AsyncMock()
    wl_repo.add.return_value = _entry(user_id, site_id, monitor=False)

    result = await ToggleWatchlistMonitor(
        user_id=user_id, site_id=site_id, monitor=False, watchlist_repository=wl_repo
    ).execute()

    expect(result.monitor).to(be_false)
    args, kwargs = wl_repo.add.call_args
    expect(args[0]).to(equal(user_id))
    expect(args[1]).to(equal(site_id))
    expect(kwargs["monitor"]).to(be_false)


async def test_remove_from_watchlist_calls_remove_by_user_and_site():
    user_id, site_id = uuid4(), uuid4()
    wl_repo = AsyncMock()
    await RemoveFromWatchlist(
        user_id=user_id, site_id=site_id, watchlist_repository=wl_repo
    ).execute()
    wl_repo.remove.assert_called_once_with(user_id, site_id)


async def test_get_alert_prefs_defaults_when_absent():
    user_id = uuid4()
    repo = AsyncMock()
    repo.get.return_value = None
    prefs = await GetAlertPrefs(
        user_id=user_id, notification_prefs_repository=repo
    ).execute()
    expect(prefs.email_enabled).to(be_true)
    expect(prefs.slack_webhook_url).to(equal(None))


async def test_update_alert_prefs_upserts():
    user_id = uuid4()
    repo = AsyncMock()
    repo.upsert.return_value = NotificationPrefs(
        user_id=user_id, email_enabled=False, slack_webhook_url="https://hooks/x"
    )
    prefs = await UpdateAlertPrefs(
        user_id=user_id,
        notification_prefs_repository=repo,
        email_enabled=False,
        slack_webhook_url="https://hooks/x",
    ).execute()
    expect(prefs.email_enabled).to(be_false)
    expect(prefs.slack_webhook_url).to(equal("https://hooks/x"))
