"""Composition tests for ``ReportPresenter`` (09-reporting §3 / spec §2).

Pure (no DB): builds ``Scan`` + ``FindingRecord`` + ``AgenticSurface`` domain
objects and asserts the two-layer dict shape the API/PDF/frontend consume.
"""

from datetime import UTC, datetime
from uuid import uuid4

from expects import be_none, contain, equal, expect

from src.scans.domain.models.agentic_surface import AgenticSurface
from src.scans.domain.models.finding import FindingRecord
from src.scans.domain.models.scan import Scan
from src.scans.presentation.presenters.report import (
    BADGE_AGENTIC_DETECTED_UNTESTED,
    BADGE_PARTIAL_COVERAGE,
    ReportPresenter,
)

_FINISHED = datetime(2026, 6, 20, 12, 0, tzinfo=UTC)


def _scan(**overrides) -> Scan:
    base = dict(
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
        summary={
            "narrative": "Owliver encontró problemas serios.",
            "top_risks": [
                {
                    "title": "XSS reflejado",
                    "severity": "high",
                    "why_it_matters": "Permite robar sesiones",
                }
            ],
        },
    )
    base.update(overrides)
    return Scan(**base)


def _finding(severity: str, **overrides) -> FindingRecord:
    base = dict(
        uuid=uuid4(),
        scan_id=uuid4(),
        site_id=uuid4(),
        source="owasp",
        tool="nuclei",
        category="A05",
        title=f"{severity} issue",
        severity=severity,
        confidence="alta",
        description="d",
        evidence={"req": "x"},
        impact="i",
        remediation="r",
        references=[],
        status="open",
        dedupe_key=f"k-{severity}-{uuid4()}",
    )
    base.update(overrides)
    return FindingRecord(**base)


def test_executive_layer_composes_from_scan_and_summary():
    report = ReportPresenter(scan=_scan(), public=False).to_dict
    exec_layer = report["executive"]

    expect(exec_layer["overallGrade"]).to(equal("C"))
    expect(exec_layer["webScore"]).to(equal(72))
    expect(exec_layer["agenticScore"]).to(equal(40))
    expect(exec_layer["narrative"]).to(equal("Owliver encontró problemas serios."))
    expect(exec_layer["topRisks"][0]["title"]).to(equal("XSS reflejado"))
    expect(exec_layer["topRisks"][0]["whyItMatters"]).to(equal("Permite robar sesiones"))


def test_technical_findings_sorted_by_severity_desc():
    findings = [_finding("low"), _finding("critical"), _finding("medium"), _finding("high")]
    report = ReportPresenter(scan=_scan(), findings=findings, public=False).to_dict

    order = [f["severity"] for f in report["technical"]["findings"]]
    expect(order).to(equal(["critical", "high", "medium", "low"]))


def test_filters_list_distinct_present_values():
    findings = [
        _finding("high", source="owasp", category="A03"),
        _finding("low", source="agentic", category="LLM01"),
    ]
    filters = ReportPresenter(scan=_scan(), findings=findings).to_dict["technical"][
        "filters"
    ]

    expect(set(filters["sources"])).to(equal({"owasp", "agentic"}))
    expect(set(filters["categories"])).to(equal({"A03", "LLM01"}))
    expect(filters["severities"]).to(equal(["high", "low"]))  # severity desc


def test_badge_agentic_detected_untested():
    scan = _scan(agentic_status="detected_not_tested", agentic_score=None)
    badges = ReportPresenter(scan=scan).to_dict["executive"]["badges"]
    expect(badges).to(contain(BADGE_AGENTIC_DETECTED_UNTESTED))


def test_badge_partial_coverage_when_status_partial():
    scan = _scan(status="partial", overall_grade="C")
    report = ReportPresenter(scan=scan).to_dict
    expect(report["executive"]["badges"]).to(contain(BADGE_PARTIAL_COVERAGE))
    expect(report["meta"]["coveragePartial"]).to(equal(True))


def test_agentic_score_null_is_not_invented():
    scan = _scan(agentic_status="no_surface", agentic_score=None)
    exec_layer = ReportPresenter(scan=scan).to_dict["executive"]
    expect(exec_layer["agenticScore"]).to(be_none)


def test_agentic_surface_inventory_is_camelcase():
    surface = AgenticSurface(
        uuid=uuid4(),
        scan_id=uuid4(),
        site_id=uuid4(),
        type="chatbot",
        vendor="intercom",
        location_url="https://x.example/widget",
        inferred_model="gpt-4o",
    )
    inventory = ReportPresenter(scan=_scan(), agentic_surfaces=[surface]).to_dict[
        "executive"
    ]["agenticSurface"]
    expect(inventory[0]["locationUrl"]).to(equal("https://x.example/widget"))
    expect(inventory[0]["inferredModel"]).to(equal("gpt-4o"))


def test_trend_counts_new_and_fixed():
    findings = [
        _finding("high", first_seen=_FINISHED),  # new (first appeared this scan)
        _finding("low", status="fixed"),
    ]
    trend = ReportPresenter(scan=_scan(), findings=findings).to_dict["technical"][
        "trend"
    ]
    expect(trend["new"]).to(equal(1))
    expect(trend["fixed"]).to(equal(1))
