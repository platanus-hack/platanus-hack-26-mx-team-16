"""DB test for the gov leaderboard order + filters (08-ranking-watchlists §3.1).

``ScanRepository.leaderboard`` must order worst-first (overall_grade ASC,
penalty_raw DESC), exclude non-gov sites and private scans, and read only the
``sites.latest_scan_id`` row. Requires the docker postgres (autouse conftest)."""

from uuid import uuid4

from expects import contain, equal, expect

from src.common.database.models.scans.scan import ScanORM
from src.common.database.models.sites.site import SiteORM
from src.scans.infrastructure.repositories.sql_scan import SQLScanRepository


async def _seed_site_scan(
    session,
    *,
    hostname: str,
    is_gov: bool,
    grade: str | None,
    penalty: int | None,
    visibility: str = "public",
) -> ScanORM:
    site = SiteORM(
        uuid=uuid4(),
        url=f"https://{hostname}",
        hostname=hostname,
        is_gov=is_gov,
    )
    session.add(site)
    await session.flush()
    scan = ScanORM(
        uuid=uuid4(),
        site_id=site.uuid,
        level="basico",
        status="done",
        visibility=visibility,
        overall_grade=grade,
        penalty_raw=penalty,
    )
    session.add(scan)
    await session.flush()
    site.latest_scan_id = scan.uuid
    await session.flush()
    return scan


async def test_leaderboard_orders_worst_first_with_penalty_tiebreak(async_session):
    # Two F sites with different penalties + one B site.
    await _seed_site_scan(
        async_session, hostname="a.gob.mx", is_gov=True, grade="F", penalty=120
    )
    await _seed_site_scan(
        async_session, hostname="b.gob.mx", is_gov=True, grade="F", penalty=300
    )
    await _seed_site_scan(
        async_session, hostname="c.gob.mx", is_gov=True, grade="B", penalty=10
    )

    repo = SQLScanRepository(session=async_session)
    rows = await repo.leaderboard(limit=50)

    grades = [r.overall_grade for r in rows]
    # F before B (worst-first).
    expect(grades[0]).to(equal("F"))
    expect(grades[-1]).to(equal("B"))
    # Within F: higher penalty_raw first (300 before 120).
    f_penalties = [r.penalty_raw for r in rows if r.overall_grade == "F"]
    expect(f_penalties).to(equal([300, 120]))


async def test_leaderboard_excludes_non_gov_and_private(async_session):
    gov = await _seed_site_scan(
        async_session, hostname="gov.gob.mx", is_gov=True, grade="C", penalty=20
    )
    await _seed_site_scan(
        async_session, hostname="private.com", is_gov=False, grade="A", penalty=0
    )
    await _seed_site_scan(
        async_session,
        hostname="priv.gob.mx",
        is_gov=True,
        grade="A",
        penalty=0,
        visibility="private",
    )

    repo = SQLScanRepository(session=async_session)
    rows = await repo.leaderboard(limit=50)

    hostnames_by_scan = {r.uuid for r in rows}
    expect(hostnames_by_scan).to(contain(gov.uuid))
    # Non-gov and private scans are absent.
    expect(len(rows)).to(equal(1))
