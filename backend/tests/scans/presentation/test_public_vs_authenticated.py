"""Public vs authenticated report (09-reporting §1).

Blinds the "one assembly path, one bifurcation" guarantee: the same scan/findings
yield an IDENTICAL executive layer and differ ONLY in
``technical.findings[*].evidence`` (public = None).
"""

from datetime import UTC, datetime
from uuid import uuid4

from expects import be_none, equal, expect

from src.scans.domain.models.finding import FindingRecord
from src.scans.domain.models.scan import Scan
from src.scans.presentation.presenters.report import (
    PublicReportPresenter,
    ReportPresenter,
)

_FINISHED = datetime(2026, 6, 20, tzinfo=UTC)


def _scan() -> Scan:
    return Scan(
        uuid=uuid4(),
        site_id=uuid4(),
        level="basico",
        status="done",
        visibility="public",
        web_score=72,
        agentic_score=40,
        overall_score=59,
        overall_grade="C",
        agentic_status="tested",
        finished_at=_FINISHED,
        summary={"narrative": "n", "top_risks": []},
    )


def _findings() -> list[FindingRecord]:
    common = dict(
        site_id=uuid4(),
        source="owasp",
        tool="nuclei",
        category="A05",
        confidence="alta",
        description="d",
        evidence={"payload": "secret-exploit"},
        impact="i",
        remediation="r",
        references=[],
        status="open",
    )
    scan_id = uuid4()
    return [
        FindingRecord(
            uuid=uuid4(),
            scan_id=scan_id,
            title="a",
            severity="high",
            dedupe_key=f"k-{uuid4()}",
            **common,
        ),
    ]


def test_executive_layer_is_identical_public_and_authenticated():
    scan = _scan()
    findings = _findings()
    auth = ReportPresenter(scan=scan, findings=findings, public=False).to_dict
    public = PublicReportPresenter(scan=scan, findings=findings).to_dict

    expect(public["executive"]).to(equal(auth["executive"]))


def test_only_difference_is_finding_evidence():
    scan = _scan()
    findings = _findings()
    auth = ReportPresenter(scan=scan, findings=findings, public=False).to_dict
    public = PublicReportPresenter(scan=scan, findings=findings).to_dict

    auth_finding = auth["technical"]["findings"][0]
    public_finding = public["technical"]["findings"][0]

    expect(public_finding["evidence"]).to(be_none)
    expect(public_finding["evidenceRedacted"]).to(equal(True))
    expect(auth_finding["evidence"]).to(equal({"payload": "secret-exploit"}))

    # Strip the one differing field — the rest of each finding must match.
    auth_rest = {k: v for k, v in auth_finding.items() if k not in ("evidence", "evidenceRedacted")}
    public_rest = {k: v for k, v in public_finding.items() if k not in ("evidence", "evidenceRedacted")}
    expect(public_rest).to(equal(auth_rest))


def test_public_report_marks_redacted_true():
    public = PublicReportPresenter(scan=_scan(), findings=_findings()).to_dict
    expect(public["redacted"]).to(equal(True))
