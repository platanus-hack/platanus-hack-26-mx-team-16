"""Composition tests for ``ReportViewPresenter`` (in-app web report, §F7).

Pure (no DB): builds ``Scan`` + ``FindingRecord`` + ``AgenticSurface`` and asserts
the **flat** dict shape the frontend ``reportSchema`` consumes
(``{ scan, explanation, topRisks, surfaces, findings }``) — distinct from the
nested PDF/``ReportPresenter`` contract.
"""

from datetime import UTC, datetime
from uuid import uuid4

from expects import contain_only, equal, expect, have_keys, not_

from src.scans.domain.models.agentic_surface import AgenticSurface
from src.scans.domain.models.finding import FindingRecord
from src.scans.domain.models.scan import Scan
from src.scans.presentation.presenters.report_view import ReportViewPresenter

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


def test_flat_shape_matches_frontend_report_schema():
    report = ReportViewPresenter(_scan(), host="x.example").to_dict
    expect(list(report.keys())).to(
        contain_only("scan", "explanation", "topRisks", "surfaces", "findings")
    )
    expect(report["scan"]["host"]).to(equal("x.example"))
    expect(report["explanation"]).to(equal("Owliver encontró problemas serios."))


def test_top_risks_map_why_it_matters_to_impact():
    risk = ReportViewPresenter(_scan()).to_dict["topRisks"][0]
    expect(risk).to(equal({"title": "XSS reflejado", "impact": "Permite robar sesiones"}))


def test_explanation_defaults_to_empty_string_without_summary():
    report = ReportViewPresenter(_scan(summary=None)).to_dict
    expect(report["explanation"]).to(equal(""))
    expect(report["topRisks"]).to(equal([]))


def test_findings_keyed_by_id_with_full_fields_sorted_desc():
    findings = [_finding("low"), _finding("critical"), _finding("high")]
    report = ReportViewPresenter(_scan(), findings=findings).to_dict

    expect([f["severity"] for f in report["findings"]]).to(
        equal(["critical", "high", "low"])
    )
    first = report["findings"][0]
    # Frontend ``findingSchema`` requires ``id`` (not ``findingId``) + ``description``.
    expect(first).to(have_keys("id", "description", "evidence", "impact", "remediation"))
    expect(first).to(not_(have_keys("findingId")))


def test_surfaces_carry_agentic_status_for_frontend_schema():
    surface = AgenticSurface(
        uuid=uuid4(),
        scan_id=uuid4(),
        site_id=uuid4(),
        type="chatbot",
        vendor="intercom",
        location_url="https://x.example/widget",
        inferred_model="gpt-4o",
    )
    inventory = ReportViewPresenter(
        _scan(agentic_status="tested"), agentic_surfaces=[surface]
    ).to_dict["surfaces"]
    expect(inventory[0]).to(
        equal(
            {
                "type": "chatbot",
                "vendor": "intercom",
                "locationUrl": "https://x.example/widget",
                "inferredModel": "gpt-4o",
                "agenticStatus": "tested",
            }
        )
    )
