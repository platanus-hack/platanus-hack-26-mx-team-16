"""Unit tests for ``EnqueueScan`` (12-api §2). DB-less — repos are mocked.

Covers: the 01-legal attestation gate (422 for active w/o authorization, never
enqueued), the Layer-1 idempotency hit (existing live scan ⇒ created=False, no
job dispatched), the fresh-create path (201 ⇒ dispatch RunScanCommand once), and
that ``authorized``/``requested_by`` are persisted via ``enqueue``.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from expects import be_false, be_true, equal, expect

from src.common.domain.enums.scans import ScanLevel, ScanStatus, ScanVisibility
from src.common.domain.legal.exceptions import AttestationRequiredError
from src.common.domain.models.user import User
from src.scans.application.commands.run_scan import RunScanCommand
from src.scans.application.use_cases.enqueue_scan import EnqueueScan
from src.scans.domain.models.scan import Scan
from src.sites.domain.models.site import Site


def _user() -> User:
    return User(uuid=uuid4(), username="tester")


def _site(is_gov: bool = False) -> Site:
    return Site(uuid=uuid4(), url="https://example.com", hostname="example.com", is_gov=is_gov)


def _scan(site_id, *, requested_by=None, status=ScanStatus.QUEUED, level=ScanLevel.BASICO) -> Scan:
    return Scan(
        uuid=uuid4(),
        site_id=site_id,
        level=str(level),
        status=str(status),
        visibility=str(ScanVisibility.PRIVATE),
        requested_by=requested_by,
    )


def _build(user, site, *, find_active=None, enqueued=None):
    site_repo = AsyncMock()
    site_repo.get_or_create.return_value = site
    scan_repo = AsyncMock()
    scan_repo.find_active.return_value = find_active
    scan_repo.enqueue.return_value = enqueued
    command_bus = AsyncMock()
    return site_repo, scan_repo, command_bus


async def test_active_level_without_attestation_raises_and_does_not_enqueue():
    user = _user()
    site = _site()
    site_repo, scan_repo, command_bus = _build(user, site)

    use_case = EnqueueScan(
        url="https://example.com",
        level=ScanLevel.INTERMEDIO,
        authorized=False,
        user=user,
        site_repository=site_repo,
        scan_repository=scan_repo,
        command_bus=command_bus,
    )

    with pytest.raises(AttestationRequiredError):
        await use_case.execute()
    scan_repo.enqueue.assert_not_called()
    command_bus.dispatch.assert_not_called()


async def test_idempotent_hit_returns_existing_without_dispatch():
    user = _user()
    site = _site()
    existing = _scan(site.uuid, requested_by=uuid4())  # owned by someone else
    site_repo, scan_repo, command_bus = _build(user, site, find_active=existing)

    result = await EnqueueScan(
        url="https://example.com",
        level=ScanLevel.BASICO,
        authorized=False,
        user=user,
        site_repository=site_repo,
        scan_repository=scan_repo,
        command_bus=command_bus,
    ).execute()

    expect(result.created).to(be_false)
    expect(result.scan.uuid).to(equal(existing.uuid))
    scan_repo.enqueue.assert_not_called()
    command_bus.dispatch.assert_not_called()


async def test_fresh_create_enqueues_and_dispatches_run_scan_command():
    user = _user()
    site = _site()
    created = _scan(site.uuid, requested_by=user.uuid)
    site_repo, scan_repo, command_bus = _build(user, site, find_active=None, enqueued=created)

    result = await EnqueueScan(
        url="https://example.com",
        level=ScanLevel.BASICO,
        authorized=False,
        user=user,
        site_repository=site_repo,
        scan_repository=scan_repo,
        command_bus=command_bus,
    ).execute()

    expect(result.created).to(be_true)
    expect(result.scan.uuid).to(equal(created.uuid))

    # enqueue persisted attestation + requester.
    _, kwargs = scan_repo.enqueue.call_args
    expect(kwargs["requested_by"]).to(equal(user.uuid))

    # dispatched exactly one RunScanCommand for this scan, run_async=True.
    command_bus.dispatch.assert_called_once()
    args, kwargs = command_bus.dispatch.call_args
    expect(args[0]).to(equal(RunScanCommand(scan_id=created.uuid)))
    expect(kwargs["run_async"]).to(be_true)


async def test_race_lost_returns_existing_and_does_not_dispatch():
    """find_active was None, but enqueue returned a scan owned by another user
    (the partial-index race winner) ⇒ idempotent hit, no dispatch."""
    user = _user()
    site = _site()
    other_winner = _scan(site.uuid, requested_by=uuid4())
    site_repo, scan_repo, command_bus = _build(user, site, find_active=None, enqueued=other_winner)

    result = await EnqueueScan(
        url="https://example.com",
        level=ScanLevel.BASICO,
        authorized=False,
        user=user,
        site_repository=site_repo,
        scan_repository=scan_repo,
        command_bus=command_bus,
    ).execute()

    expect(result.created).to(be_false)
    command_bus.dispatch.assert_not_called()


async def test_active_with_attestation_is_private():
    user = _user()
    site = _site(is_gov=True)  # even gov: active level is private
    created = _scan(site.uuid, requested_by=user.uuid, level=ScanLevel.AVANZADO)
    site_repo, scan_repo, command_bus = _build(user, site, find_active=None, enqueued=created)

    await EnqueueScan(
        url="https://gob.mx",
        level=ScanLevel.AVANZADO,
        authorized=True,
        user=user,
        site_repository=site_repo,
        scan_repository=scan_repo,
        command_bus=command_bus,
    ).execute()

    _, kwargs = scan_repo.enqueue.call_args
    expect(kwargs["visibility"]).to(equal(str(ScanVisibility.PRIVATE)))
