"""PDF render tests (09-reporting §4.2).

The HTML assembly is pure and tested directly; the engine boundary is exercised
via a fake engine so the suite runs without WeasyPrint/Playwright installed (the
PDF E2E is deferred until a real engine dependency is present).
"""

import sys
import types
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from expects import be_a, contain, equal, expect

from src.scans.domain.models.finding import FindingRecord
from src.scans.domain.models.scan import Scan
from src.scans.infrastructure.pdf.render import (
    PdfEngineError,
    render_report_html,
    render_report_pdf,
)
from src.scans.presentation.presenters.report import ReportPresenter


def _report(public: bool = False) -> dict:
    scan = Scan(
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
        finished_at=datetime(2026, 6, 20, tzinfo=UTC),
        summary={"narrative": "Owliver te explica", "top_risks": []},
    )
    finding = FindingRecord(
        uuid=uuid4(),
        scan_id=scan.uuid,
        site_id=scan.site_id,
        source="owasp",
        tool="nuclei",
        category="A05",
        title="header missing",
        severity="medium",
        confidence="alta",
        description="d",
        evidence={"screenshots": ["1.png"]},
        impact="i",
        remediation="r",
        references=[],
        status="open",
        dedupe_key=f"k-{uuid4()}",
    )
    return ReportPresenter(scan=scan, findings=[finding], public=public).to_dict


def test_html_references_static_screenshot_route():
    report = _report()
    html = render_report_html(report, base_url="http://host:8200")
    scan_id = report["meta"]["scanId"]

    expect(html).to(contain(f"http://host:8200/static/scans/{scan_id}/1.png"))
    expect(html).to(contain("Owliver te explica"))


def test_html_omits_evidence_screenshots_in_public_report():
    report = _report(public=True)
    html = render_report_html(report, base_url="http://host:8200")
    # Public report redacts evidence (None), so no attack screenshot is embedded.
    expect(html).to(contain("Evidencia oculta"))
    expect(html).to_not(contain("/1.png"))


def test_render_pdf_uses_weasyprint_engine(monkeypatch):
    captured = {}

    class _FakeHTML:
        def __init__(self, *, string, base_url):
            captured["string"] = string
            captured["base_url"] = base_url

        def write_pdf(self):
            return b"%PDF-1.7 fake"

    fake_module = types.ModuleType("weasyprint")
    fake_module.HTML = _FakeHTML
    monkeypatch.setitem(sys.modules, "weasyprint", fake_module)
    monkeypatch.setattr(
        "src.scans.infrastructure.pdf.render._resolve_engine",
        lambda: "weasyprint",
    )

    out = render_report_pdf(_report(), base_url="http://host:8200")

    expect(out).to(be_a(bytes))
    expect(len(out) > 0).to(equal(True))
    expect(captured["base_url"]).to(equal("http://host:8200"))


def test_render_pdf_raises_clean_error_on_unknown_engine(monkeypatch):
    monkeypatch.setattr(
        "src.scans.infrastructure.pdf.render._resolve_engine",
        lambda: "bogus",
    )
    with pytest.raises(PdfEngineError):
        render_report_pdf(_report(), base_url="http://host:8200")


def test_render_html_fails_loud_on_malformed_report():
    with pytest.raises(KeyError):
        render_report_html({"executive": {}}, base_url="http://host")
