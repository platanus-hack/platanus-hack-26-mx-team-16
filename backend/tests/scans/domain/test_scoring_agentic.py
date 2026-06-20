"""Agentic-status modulation tests (07-scoring §3/§6.1) — pure domain."""

from __future__ import annotations

from expects import be_false, be_none, be_true, equal, expect

from src.common.domain.enums.scans import AgenticStatus
from src.scans.domain.services.scoring import ScoreInput, compute_score
from tests.scans.domain._factories import make_finding


def _web_and_agentic() -> list:
    # web: 1 high/alta -> penalty 20 -> web_score 80
    # agentic: 1 critical/alta -> penalty 40 -> agentic_score 60
    return [
        make_finding(source="owasp", severity="high", confidence="alta", category="A01"),
        make_finding(
            source="agentic",
            severity="critical",
            confidence="alta",
            category="LLM07",
            tool="garak",
            endpoint=None,
        ),
    ]


def test_tested_averages_web_and_agentic() -> None:
    result = compute_score(
        ScoreInput(findings=_web_and_agentic(), agentic_status=AgenticStatus.TESTED)
    )

    expect(result.web_score).to(equal(80))
    expect(result.agentic_score).to(equal(60))
    # round(0.6*80 + 0.4*60) = round(48 + 24) = 72
    expect(result.overall_score).to(equal(72))
    expect(result.overall_grade).to(equal("C"))
    expect(result.agentic_detected_untested).to(be_false)


def test_tested_overall_is_rounded() -> None:
    # web 1 high/alta -> 80; agentic 1 high/media -> penalty 14 -> agentic 86
    findings = [
        make_finding(source="owasp", severity="high", confidence="alta"),
        make_finding(
            source="agentic",
            severity="high",
            confidence="media",
            tool="garak",
            endpoint=None,
        ),
    ]
    result = compute_score(
        ScoreInput(findings=findings, agentic_status=AgenticStatus.TESTED)
    )

    # agentic penalty 20*0.7=14 -> 86; round(0.6*80 + 0.4*86) = round(48 + 34.4) = 82
    expect(result.agentic_score).to(equal(86))
    expect(result.overall_score).to(equal(82))


def test_no_surface_uses_web_score_and_no_agentic() -> None:
    result = compute_score(
        ScoreInput(findings=_web_and_agentic(), agentic_status=AgenticStatus.NO_SURFACE)
    )

    expect(result.overall_score).to(equal(result.web_score))
    expect(result.overall_score).to(equal(80))
    expect(result.agentic_score).to(be_none)
    expect(result.agentic_detected_untested).to(be_false)


def test_detected_not_tested_uses_web_score_with_badge() -> None:
    result = compute_score(
        ScoreInput(
            findings=_web_and_agentic(),
            agentic_status=AgenticStatus.DETECTED_NOT_TESTED,
        )
    )

    # overall == web_score, never averaged, never rewarded with 100
    expect(result.overall_score).to(equal(result.web_score))
    expect(result.overall_score).to(equal(80))
    expect(result.agentic_score).to(be_none)
    expect(result.agentic_detected_untested).to(be_true)


def test_detected_not_tested_never_rewards_100() -> None:
    # even a poor web site with an undetected-but-present agentic surface stays
    # at web_score, the badge flag fires, and agentic is not silently a perfect 100.
    findings = [make_finding(source="owasp", severity="critical", confidence="alta")]
    result = compute_score(
        ScoreInput(findings=findings, agentic_status=AgenticStatus.DETECTED_NOT_TESTED)
    )

    expect(result.web_score).to(equal(60))
    expect(result.overall_score).to(equal(60))
    expect(result.agentic_score).to(be_none)
    expect(result.agentic_detected_untested).to(be_true)
