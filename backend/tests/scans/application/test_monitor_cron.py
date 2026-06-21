"""Use-case tests for the monitoring cron body + the shared idempotent enqueue
(08-ranking-watchlists §4.1/§4.2). Mocked repos/bus, DB-less."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from expects import be_false, be_true, equal, expect

from src.common.domain.enums.scans import ScanLevel, ScanVisibility
from src.common.domain.legal.exceptions import AutomaticActiveScanError
from src.scans.application.commands.enqueue_monitor_scan import enqueue_automatic_scan
from src.scans.application.commands.monitor_cron import MonitorCronHandler
from src.scans.domain.models.scan import Scan
from src.sites.domain.models.site import Site
from src.sites.domain.models.watchlist import WatchlistEntry


def _site(*, is_gov, site_id=None) -> Site:
    return Site(
        uuid=site_id or uuid4(),
        url="https://x.com",
        hostname="x.com",
        is_gov=is_gov,
    )


def _scan(site_id, *, status="queued") -> Scan:
    return Scan(
        uuid=uuid4(), site_id=site_id, level="basico", status=status,
        visibility="public", requested_by=None,
    )


# ---- enqueue_automatic_scan (the shared idempotency) ----

async def test_enqueue_gov_active_level_raises():
    scan_repo = AsyncMock()
    bus = AsyncMock()
    # The coroutine must be AWAITED for the gov-active-level guard to run and
    # raise; ``expect(coro).to(raise_error(...))`` never awaits it (the matcher
    # only inspects the un-awaited coroutine object). Await it under pytest.raises.
    with pytest.raises(AutomaticActiveScanError):
        await enqueue_automatic_scan(
            site_id=uuid4(),
            level=ScanLevel.AVANZADO,
            visibility=ScanVisibility.PUBLIC,
            scan_repository=scan_repo,
            command_bus=bus,
            is_gov=True,
        )


async def test_enqueue_idempotent_no_op_when_live_scan_exists():
    site_id = uuid4()
    scan_repo = AsyncMock()
    scan_repo.find_active.return_value = _scan(site_id, status="running")
    bus = AsyncMock()

    scan, created = await enqueue_automatic_scan(
        site_id=site_id,
        level=ScanLevel.BASICO,
        visibility=ScanVisibility.PUBLIC,
        scan_repository=scan_repo,
        command_bus=bus,
        is_gov=True,
    )
    expect(created).to(be_false)
    scan_repo.enqueue.assert_not_called()
    bus.dispatch.assert_not_called()


async def test_enqueue_creates_and_dispatches_run_scan():
    site_id = uuid4()
    scan_repo = AsyncMock()
    scan_repo.find_active.return_value = None
    # ``enqueue`` reports ``(scan, created)``; created=True ⇒ dispatch once.
    scan_repo.enqueue.return_value = (_scan(site_id, status="queued"), True)
    bus = AsyncMock()

    scan, created = await enqueue_automatic_scan(
        site_id=site_id,
        level=ScanLevel.BASICO,
        visibility=ScanVisibility.PUBLIC,
        scan_repository=scan_repo,
        command_bus=bus,
        is_gov=True,
    )
    expect(created).to(be_true)
    bus.dispatch.assert_called_once()


# ---- MonitorCronHandler ----

async def test_cron_reenqueues_watchlist_and_gov_seed():
    gov_site = _site(is_gov=True)
    wl_site = _site(is_gov=False)

    site_repo = AsyncMock()
    site_repo.list_gov.return_value = [gov_site]
    site_repo.find.return_value = wl_site
    wl_repo = AsyncMock()
    wl_repo.sites_with_monitor_true.return_value = [
        WatchlistEntry(uuid=uuid4(), user_id=uuid4(), site_id=wl_site.uuid, monitor=True)
    ]
    scan_repo = AsyncMock()
    scan_repo.find_active.return_value = None
    scan_repo.enqueue.side_effect = lambda site_id, level, **kw: (_scan(site_id), True)
    bus = AsyncMock()

    handler = MonitorCronHandler(
        site_repository=site_repo,
        watchlist_repository=wl_repo,
        scan_repository=scan_repo,
        command_bus=bus,
        monitor_level_default=ScanLevel.BASICO,
    )
    created = await handler.execute()

    # One watchlist site + one gov site = two enqueued scans.
    expect(created).to(equal(2))
    # Gov site is always enqueued at the basic level.
    gov_calls = [c for c in scan_repo.enqueue.call_args_list if c.args[0] == gov_site.uuid]
    expect(gov_calls[0].args[1]).to(equal(str(ScanLevel.BASICO)))


async def test_cron_dedupes_site_present_in_both_watchlist_and_gov():
    shared = _site(is_gov=True)

    site_repo = AsyncMock()
    site_repo.list_gov.return_value = [shared]
    site_repo.find.return_value = shared
    wl_repo = AsyncMock()
    wl_repo.sites_with_monitor_true.return_value = [
        WatchlistEntry(uuid=uuid4(), user_id=uuid4(), site_id=shared.uuid, monitor=True)
    ]
    scan_repo = AsyncMock()
    scan_repo.find_active.return_value = None
    scan_repo.enqueue.side_effect = lambda site_id, level, **kw: (_scan(site_id), True)
    bus = AsyncMock()

    handler = MonitorCronHandler(
        site_repository=site_repo,
        watchlist_repository=wl_repo,
        scan_repository=scan_repo,
        command_bus=bus,
    )
    created = await handler.execute()

    # The shared site is enqueued exactly once (deduped across both sources).
    expect(created).to(equal(1))
    expect(scan_repo.enqueue.call_count).to(equal(1))
