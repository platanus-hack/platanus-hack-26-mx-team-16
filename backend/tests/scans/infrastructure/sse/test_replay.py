"""``make_scan_event_replay`` over real Postgres (10 §4.1).

Verifies the replay window reads ``seq > since_seq ORDER BY seq ASC``, isolates
by ``scan_id``, and yields JSON-safe event dicts for ``stream_sse``. Requires the
docker postgres (autouse conftest provides the schema/session).
"""

from datetime import UTC, datetime
from uuid import uuid4

from expects import be_empty, equal, expect

from src.common.database.models.scans.scan import ScanORM
from src.common.database.models.sites.site import SiteORM
from src.scans.domain.contracts.events import ScanEvent
from src.scans.infrastructure.repositories.sql_scan_event import SQLScanEventRepository
from src.scans.infrastructure.sse.replay import make_scan_event_replay


async def _seed_scan(session) -> ScanORM:
    site = SiteORM(uuid=uuid4(), url="https://t.example.com", hostname="t.example.com")
    session.add(site)
    await session.flush()
    scan = ScanORM(uuid=uuid4(), site_id=site.uuid, level="basico", visibility="public")
    session.add(scan)
    await session.flush()
    return scan


def _event(scan_id, seq: int) -> ScanEvent:
    return ScanEvent(
        scan_id=scan_id,
        seq=seq,
        ts=datetime.now(UTC),
        type="phase",
        message=f"event {seq}",
    )


async def _collect(replay):
    return [ev async for ev in replay()]


async def test_replay_full_from_zero_cursor(async_session):
    scan = await _seed_scan(async_session)
    repo = SQLScanEventRepository(session=async_session)
    for seq in (1, 2, 3):
        await repo.append(_event(scan.uuid, seq))

    replay = await make_scan_event_replay(repo, scan.uuid, since_seq=0)
    events = await _collect(replay)

    expect([e["seq"] for e in events]).to(equal([1, 2, 3]))


async def test_replay_only_after_cursor(async_session):
    scan = await _seed_scan(async_session)
    repo = SQLScanEventRepository(session=async_session)
    for seq in (1, 2, 3, 4):
        await repo.append(_event(scan.uuid, seq))

    replay = await make_scan_event_replay(repo, scan.uuid, since_seq=2)
    events = await _collect(replay)

    expect([e["seq"] for e in events]).to(equal([3, 4]))


async def test_replay_at_last_cursor_is_empty(async_session):
    scan = await _seed_scan(async_session)
    repo = SQLScanEventRepository(session=async_session)
    for seq in (1, 2, 3):
        await repo.append(_event(scan.uuid, seq))

    replay = await make_scan_event_replay(repo, scan.uuid, since_seq=3)
    events = await _collect(replay)

    expect(events).to(be_empty)


async def test_replay_ordered_by_seq_regardless_of_insert_order(async_session):
    scan = await _seed_scan(async_session)
    repo = SQLScanEventRepository(session=async_session)
    for seq in (3, 1, 2):  # inserted out of order
        await repo.append(_event(scan.uuid, seq))

    replay = await make_scan_event_replay(repo, scan.uuid, since_seq=0)
    events = await _collect(replay)

    expect([e["seq"] for e in events]).to(equal([1, 2, 3]))


async def test_replay_isolated_by_scan_id(async_session):
    scan_a = await _seed_scan(async_session)
    scan_b = await _seed_scan(async_session)
    repo = SQLScanEventRepository(session=async_session)
    await repo.append(_event(scan_a.uuid, 1))
    await repo.append(_event(scan_b.uuid, 1))
    await repo.append(_event(scan_b.uuid, 2))

    replay = await make_scan_event_replay(repo, scan_a.uuid, since_seq=0)
    events = await _collect(replay)

    expect([e["seq"] for e in events]).to(equal([1]))
    expect(str(events[0]["scan_id"])).to(equal(str(scan_a.uuid)))
