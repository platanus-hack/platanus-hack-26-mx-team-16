"""Unit tests for ``ListScanFindings`` (12-api §"Lectura"). DB-less."""

from unittest.mock import AsyncMock
from uuid import uuid4

from expects import be_none, equal, expect

from src.scans.application.use_cases.list_scan_findings import ListScanFindings
from src.scans.domain.models.finding import FindingRecord


def _finding(severity: str) -> FindingRecord:
    scan_id = uuid4()
    return FindingRecord(
        uuid=uuid4(),
        scan_id=scan_id,
        site_id=uuid4(),
        source="owasp",
        tool="nuclei",
        category="A05",
        title=f"{severity} issue",
        severity=severity,
        confidence="alta",
        description="d",
        impact="i",
        remediation="r",
        status="open",
        dedupe_key=f"k-{severity}-{uuid4()}",
    )


def _use_case(findings, *, limit=25, cursor=None):
    repo = AsyncMock()
    repo.list_for_scan.return_value = findings
    return ListScanFindings(
        scan_id=uuid4(), finding_repository=repo, limit=limit, cursor=cursor
    )


async def test_findings_sorted_by_severity_desc():
    findings = [_finding("low"), _finding("critical"), _finding("medium"), _finding("high")]
    page = await _use_case(findings).execute()
    severities = [f.severity for f in page.items]
    expect(severities).to(equal(["critical", "high", "medium", "low"]))


async def test_findings_pagination_emits_next_cursor_and_resumes():
    findings = [_finding("critical"), _finding("high"), _finding("medium"), _finding("low")]
    first = await _use_case(findings, limit=2).execute()
    expect(len(first.items)).to(equal(2))
    expect(first.next_cursor).to_not(be_none)

    # Resume from the cursor — should return the remaining 2, still severity desc.
    second = await _use_case(findings, limit=2, cursor=first.next_cursor).execute()
    severities = [f.severity for f in second.items]
    expect(severities).to(equal(["medium", "low"]))
    expect(second.next_cursor).to(be_none)
