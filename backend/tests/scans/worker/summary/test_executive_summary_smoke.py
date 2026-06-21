"""Executive-summary synthesis smoke (05-agent-team plan §6/§9).

The ONLY structured-output path in the worker. NEVER a real Anthropic call: the
Agno model/agent is mocked. Verifies ``synthesize_summary`` returns a valid
:class:`ExecutiveSummary` over the compact (evidence-free) summary, that the
compact builder drops ``evidence`` + info-only metas, and that the no-key path
falls back deterministically.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from expects import be_a, be_below, contain, equal, expect, have_len

from src.scans.domain.contracts.finding import Finding
from src.scans.domain.services.scoring import ScoreResult
from src.scans.worker.summary import (
    OPUS_SUMMARY_MAX_TOKENS,
    ExecutiveSummary,
    TopRisk,
    compact,
    synthesize_summary,
)


def _finding(severity: str = "high", title: str = "SQLi", category: str = "A03") -> Finding:
    return Finding(
        source="owasp",
        tool="nuclei",
        category=category,
        title=title,
        severity=severity,
        confidence="alta",
        description="d",
        evidence={"payload": "x" * 5000},  # large evidence MUST be dropped by compact()
        affected_url="https://gob.mx/login",
        impact="Robo de datos",
        remediation="parametriza",
    )


def _score() -> ScoreResult:
    return ScoreResult(
        web_score=62,
        agentic_score=100,
        overall_score=68,
        overall_grade="C",
        penalty_raw=38.0,
        coverage_partial=False,
        agentic_detected_untested=False,
    )


def test_compact_drops_evidence_and_info_metas():
    findings = [
        _finding(severity="critical", title="RCE"),
        _finding(severity="info", title="Cobertura incompleta: nuclei"),
    ]
    out = compact(findings)
    # No evidence anywhere in the compact payload.
    blob = str(out)
    expect("payload" in blob).to(equal(False))
    # info-only metas are not surfaced as top findings (they don't drive narrative).
    top_titles = [t["title"] for t in out["top_findings"]]
    expect(top_titles).to(contain("RCE"))
    expect("Cobertura incompleta: nuclei" in top_titles).to(equal(False))
    expect(out["total"]).to(equal(2))


async def test_synthesize_summary_uses_injected_model_returns_structured():
    findings = [_finding(severity="critical", title="RCE", category="A01")]

    class FakeResult:
        content = ExecutiveSummary(
            narrative="El sitio tiene riesgos críticos.",
            top_risks=[TopRisk(title="RCE", severity="critical", why_it_matters="control total")],
        )

    fake_agent = AsyncMock()
    fake_agent.arun = AsyncMock(return_value=FakeResult())

    summary = await synthesize_summary(findings, _score(), model=fake_agent)

    expect(summary).to(be_a(ExecutiveSummary))
    expect(summary.top_risks).to(have_len(1))
    expect(summary.narrative).to(contain("crític"))
    # The prompt handed to Opus stays small (compact, evidence-free).
    prompt = fake_agent.arun.await_args.args[0]
    expect("x" * 5000 not in prompt).to(equal(True))
    expect(len(prompt)).to(be_below(OPUS_SUMMARY_MAX_TOKENS * 4))  # ~4 chars/token bound


async def test_synthesize_summary_falls_back_without_model_or_key(monkeypatch):
    # No injected model and no ANTHROPIC_API_KEY ⇒ deterministic fallback, still a
    # valid ExecutiveSummary (never raises, never calls the API). Force the key to
    # None so the test is hermetic regardless of the runner's environment.
    from src.common import settings as settings_module

    monkeypatch.setattr(settings_module.settings, "ANTHROPIC_API_KEY", None, raising=False)
    findings = [_finding(severity="high", title="XSS")]
    summary = await synthesize_summary(findings, _score(), model=None)
    expect(summary).to(be_a(ExecutiveSummary))
    expect(summary.narrative).to(contain("C"))  # grade surfaced in the narrative
