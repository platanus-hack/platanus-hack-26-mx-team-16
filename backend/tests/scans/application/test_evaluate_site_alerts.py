"""Use-case tests for the site-level monitoring alert decision
(08-ranking-watchlists §4.3). Mocked repos, DB-less."""

from unittest.mock import AsyncMock
from uuid import uuid4

from expects import be_empty, equal, expect

from src.scans.application.use_cases.evaluate_site_alerts import EvaluateSiteAlerts
from src.scans.domain.models.finding import FindingRecord
from src.scans.domain.models.scan import Scan
from src.sites.domain.models.notification_prefs import NotificationPrefs
from src.sites.domain.models.site import Site


def _scan(*, requested_by=None, grade="D", site_id=None) -> Scan:
    return Scan(
        uuid=uuid4(),
        site_id=site_id or uuid4(),
        level="basico",
        status="done",
        visibility="private",
        requested_by=requested_by,
        overall_grade=grade,
    )


def _site(owner_user_id) -> Site:
    return Site(
        uuid=uuid4(),
        url="https://x.com",
        hostname="x.com",
        is_gov=False,
        owner_user_id=owner_user_id,
    )


def _critical(site_id) -> FindingRecord:
    return FindingRecord(
        uuid=uuid4(),
        scan_id=uuid4(),
        site_id=site_id,
        source="owasp",
        tool="nuclei",
        category="A05",
        title="t",
        severity="critical",
        confidence="alta",
        description="d",
        impact="i",
        remediation="r",
        status="open",
        dedupe_key="dk",
    )


def _user_with_email(user_id, email="owner@example.com"):
    user = AsyncMock()
    user.email_address.email = email
    return user


def _deps(*, scan, prev_scan, criticals, site, prefs, owner):
    scan_repo = AsyncMock()
    scan_repo.find.return_value = scan
    scan_repo.previous_graded_scan.return_value = prev_scan
    finding_repo = AsyncMock()
    finding_repo.criticals_first_seen_in.return_value = criticals
    site_repo = AsyncMock()
    site_repo.find.return_value = site
    prefs_repo = AsyncMock()
    prefs_repo.get.return_value = prefs
    user_repo = AsyncMock()
    user_repo.find.return_value = owner
    alert_repo = AsyncMock()
    alert_repo.log.side_effect = lambda alert: alert
    bus = AsyncMock()
    return EvaluateSiteAlerts(
        scan_id=scan.uuid,
        scan_repository=scan_repo,
        finding_repository=finding_repo,
        site_repository=site_repo,
        notification_prefs_repository=prefs_repo,
        user_repository=user_repo,
        alert_repository=alert_repo,
        command_bus=bus,
    ), alert_repo, bus


async def test_manual_scan_never_alerts():
    user_id = uuid4()
    scan = _scan(requested_by=user_id, grade="F")
    uc, alert_repo, _ = _deps(
        scan=scan,
        prev_scan=_scan(grade="A"),
        criticals=[],
        site=_site(user_id),
        prefs=NotificationPrefs(user_id=user_id),
        owner=_user_with_email(user_id),
    )
    result = await uc.execute()
    expect(result).to(be_empty)
    alert_repo.log.assert_not_called()


async def test_grade_drop_dispatches_alert():
    owner_id = uuid4()
    site_id = uuid4()
    scan = _scan(requested_by=None, grade="D", site_id=site_id)
    prev = _scan(grade="B", site_id=site_id)
    uc, alert_repo, bus = _deps(
        scan=scan,
        prev_scan=prev,
        criticals=[],
        site=_site(owner_id),
        prefs=NotificationPrefs(user_id=owner_id, email_enabled=True),
        owner=_user_with_email(owner_id),
    )
    result = await uc.execute()
    expect(len(result)).to(equal(1))  # email channel logged
    bus.dispatch.assert_called()  # SendEmailCommand dispatched


async def test_new_critical_dispatches_even_without_grade_drop():
    owner_id = uuid4()
    site_id = uuid4()
    scan = _scan(requested_by=None, grade="C", site_id=site_id)
    prev = _scan(grade="C", site_id=site_id)  # same grade, no drop
    uc, alert_repo, _ = _deps(
        scan=scan,
        prev_scan=prev,
        criticals=[_critical(site_id)],
        site=_site(owner_id),
        prefs=NotificationPrefs(user_id=owner_id, email_enabled=True),
        owner=_user_with_email(owner_id),
    )
    result = await uc.execute()
    expect(len(result)).to(equal(1))


async def test_no_drop_no_new_critical_does_not_alert():
    owner_id = uuid4()
    site_id = uuid4()
    scan = _scan(requested_by=None, grade="C", site_id=site_id)
    prev = _scan(grade="C", site_id=site_id)
    uc, alert_repo, _ = _deps(
        scan=scan,
        prev_scan=prev,
        criticals=[],
        site=_site(owner_id),
        prefs=NotificationPrefs(user_id=owner_id),
        owner=_user_with_email(owner_id),
    )
    result = await uc.execute()
    expect(result).to(be_empty)
    alert_repo.log.assert_not_called()


async def test_gov_site_without_owner_never_alerts():
    site_id = uuid4()
    scan = _scan(requested_by=None, grade="F", site_id=site_id)
    prev = _scan(grade="A", site_id=site_id)
    gov_site = Site(
        uuid=site_id, url="https://x.gob.mx", hostname="x.gob.mx",
        is_gov=True, owner_user_id=None,
    )
    uc, alert_repo, _ = _deps(
        scan=scan,
        prev_scan=prev,
        criticals=[_critical(site_id)],
        site=gov_site,
        prefs=None,
        owner=None,
    )
    result = await uc.execute()
    expect(result).to(be_empty)
    alert_repo.log.assert_not_called()
