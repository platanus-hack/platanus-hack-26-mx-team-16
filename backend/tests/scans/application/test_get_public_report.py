"""Unit tests for ``GetPublicReport`` — the 404/410 token contract (12-api). DB-less."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from expects import equal, expect

from src.scans.application.use_cases.get_public_report import GetPublicReport
from src.scans.domain.models.public_report import PublicReport
from src.scans.domain.models.scan import Scan
from src.scans.presentation.exceptions import (
    PublicReportGoneError,
    PublicReportNotFoundError,
)


def _report(*, expires_at=None, revoked_at=None, scan_id=None) -> PublicReport:
    return PublicReport(
        uuid=uuid4(),
        token="tok",
        scan_id=scan_id or uuid4(),
        expires_at=expires_at,
        revoked_at=revoked_at,
    )


def _scan(uuid) -> Scan:
    return Scan(
        uuid=uuid,
        site_id=uuid4(),
        level="basico",
        status="done",
        visibility="public",
    )


def _use_case(*, report, scan=None):
    report_repo = AsyncMock()
    report_repo.find_by_token.return_value = report
    scan_repo = AsyncMock()
    scan_repo.find.return_value = scan
    return GetPublicReport(
        token="tok", public_report_repository=report_repo, scan_repository=scan_repo
    )


async def test_unknown_token_raises_not_found():
    with pytest.raises(PublicReportNotFoundError):
        await _use_case(report=None).execute()


async def test_expired_token_raises_gone():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    with pytest.raises(PublicReportGoneError):
        await _use_case(report=_report(expires_at=past)).execute()


async def test_revoked_token_raises_gone():
    now = datetime.now(timezone.utc)
    with pytest.raises(PublicReportGoneError):
        await _use_case(report=_report(revoked_at=now)).execute()


async def test_valid_token_returns_scan():
    scan_id = uuid4()
    future = datetime.now(timezone.utc) + timedelta(days=3)
    report = _report(expires_at=future, scan_id=scan_id)
    view = await _use_case(report=report, scan=_scan(scan_id)).execute()
    expect(view.scan.uuid).to(equal(scan_id))
