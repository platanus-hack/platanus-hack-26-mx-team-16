"""DB tests for site-level change detection + alert log
(08-ranking-watchlists §4.2/§4.3/§5.1). Requires docker postgres."""

import uuid
from datetime import UTC, datetime, timedelta
from itertools import count
from uuid import uuid4

from expects import be_empty, equal, expect

from src.common.database.models.scans.scan import ScanORM
from src.common.database.models.sites.site import SiteORM
from src.common.database.models.user import UserORM
from src.scans.domain.models.alert import Alert
from src.scans.domain.models.finding import FindingRecord
from src.scans.infrastructure.repositories.sql_alert import SQLAlertRepository
from src.scans.infrastructure.repositories.sql_finding import SQLFindingRepository
from src.scans.infrastructure.repositories.sql_scan import SQLScanRepository

# Monotonic clock for seeding distinct scan ``created_at`` values. Scans seeded in
# one DB transaction would otherwise share ``func.now()`` (Postgres transaction
# start time), making "previous scan by time" ambiguous. Real scans always run
# minutes/days apart, so explicit increasing timestamps mirror production.
_BASE_TS = datetime(2026, 1, 1, tzinfo=UTC)
_seq = count()


async def _seed_site(session, *, is_gov=True, hostname="x.gob.mx") -> SiteORM:
    site = SiteORM(uuid=uuid4(), url=f"https://{hostname}", hostname=hostname, is_gov=is_gov)
    session.add(site)
    await session.flush()
    return site


async def _seed_user(session) -> UserORM:
    n = next(_seq)
    user = UserORM(uuid=uuid4(), username=f"alert-owner-{n}-{uuid4().hex[:8]}")
    session.add(user)
    await session.flush()
    return user


async def _seed_scan(session, site_id, *, status="done", grade="C") -> ScanORM:
    scan = ScanORM(
        uuid=uuid4(), site_id=site_id, level="basico", status=status,
        visibility="public", overall_grade=grade,
        # Distinct, increasing timestamp so ``previous_graded_scan`` is deterministic.
        created_at=_BASE_TS + timedelta(seconds=next(_seq)),
    )
    session.add(scan)
    await session.flush()
    return scan


def _finding(scan_id, site_id, *, severity="critical", key="dk") -> FindingRecord:
    return FindingRecord(
        uuid=uuid.uuid4(), scan_id=scan_id, site_id=site_id,
        source="owasp", tool="nuclei", category="A05", title="t",
        severity=severity, confidence="alta", description="d", impact="i",
        remediation="r", status="open", dedupe_key=key,
    )


async def test_new_critical_first_seen_in_scan(async_session):
    site = await _seed_site(async_session)
    scan = await _seed_scan(async_session, site.uuid)
    finding_repo = SQLFindingRepository(session=async_session)

    await finding_repo.upsert(_finding(scan.uuid, site.uuid, key="new-key"))

    new_crit = await finding_repo.criticals_first_seen_in(scan.uuid)
    expect(len(new_crit)).to(equal(1))
    expect(new_crit[0].dedupe_key).to(equal("new-key"))


async def test_reseen_critical_is_not_new(async_session):
    site = await _seed_site(async_session)
    scan1 = await _seed_scan(async_session, site.uuid)
    finding_repo = SQLFindingRepository(session=async_session)

    # First scan: finding appears (first_seen == last_seen).
    await finding_repo.upsert(_finding(scan1.uuid, site.uuid, key="persist"))

    # Second scan: same dedupe_key re-seen (UPSERT bumps last_seen only).
    scan2 = await _seed_scan(async_session, site.uuid)
    await finding_repo.upsert(_finding(scan2.uuid, site.uuid, key="persist"))

    # It is NOT new at the second scan (first_seen < last_seen now).
    new_crit = await finding_repo.criticals_first_seen_in(scan2.uuid)
    expect(new_crit).to(be_empty)


async def test_disappeared_finding_marked_fixed(async_session):
    site = await _seed_site(async_session)
    scan1 = await _seed_scan(async_session, site.uuid)
    finding_repo = SQLFindingRepository(session=async_session)
    await finding_repo.upsert(_finding(scan1.uuid, site.uuid, key="gone"))

    # Re-scan that no longer reports "gone".
    fixed_count = await finding_repo.mark_fixed_absent(site.uuid, present_keys=["other"])
    expect(fixed_count).to(equal(1))

    site_findings = await finding_repo.list_for_site(site.uuid)
    expect(site_findings[0].status).to(equal("fixed"))


async def test_previous_graded_scan_skips_first_scan(async_session):
    site = await _seed_site(async_session)
    scan_repo = SQLScanRepository(session=async_session)

    first = await _seed_scan(async_session, site.uuid, grade="B")
    # No prior graded scan exists before the first.
    prev = await scan_repo.previous_graded_scan(site.uuid, before=first.uuid)
    expect(prev).to(equal(None))

    second = await _seed_scan(async_session, site.uuid, grade="D")
    prev2 = await scan_repo.previous_graded_scan(site.uuid, before=second.uuid)
    expect(prev2.uuid).to(equal(first.uuid))


async def test_alert_log_records_channel_and_ids(async_session):
    site = await _seed_site(async_session)
    scan = await _seed_scan(async_session, site.uuid)
    # alerts.user_id has a real FK to users — seed the owner row first.
    user_id = (await _seed_user(async_session)).uuid
    alert_repo = SQLAlertRepository(session=async_session)

    logged = await alert_repo.log(
        Alert(
            uuid=uuid4(), user_id=user_id, site_id=site.uuid, scan_id=scan.uuid,
            type="grade_drop", message="grade dropped B -> D", channel="slack",
        )
    )
    expect(logged.channel).to(equal("slack"))
    expect(logged.site_id).to(equal(site.uuid))

    rows = await alert_repo.list_for_user(user_id)
    expect(len(rows)).to(equal(1))
