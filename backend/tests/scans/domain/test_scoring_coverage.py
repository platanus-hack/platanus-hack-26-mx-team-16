"""Partial-coverage cap-to-C tests (07-scoring §4/§5.2) — pure domain."""

from __future__ import annotations

import pytest
from expects import be_false, be_true, equal, expect

from src.common.domain.enums.scans import AgenticStatus
from src.scans.domain.services.scoring import (
    ScoreInput,
    compute_score,
    dimension_grade,
)
from tests.scans.domain._factories import make_finding


def _clean_scan(*, partial: bool) -> ScoreInput:
    # zero findings -> overall_score 100 -> would be A without the cap
    return ScoreInput(
        findings=[],
        agentic_status=AgenticStatus.NO_SURFACE,
        partial_coverage=partial,
    )


def test_partial_coverage_caps_an_a_grade_to_c() -> None:
    result = compute_score(_clean_scan(partial=True))

    expect(result.overall_grade).to(equal("C"))
    expect(result.coverage_partial).to(be_true)
    # the numeric score is NOT touched by the cap (§5.2)
    expect(result.overall_score).to(equal(100))
    expect(result.web_score).to(equal(100))


def test_no_partial_coverage_keeps_the_a_grade() -> None:
    result = compute_score(_clean_scan(partial=False))

    expect(result.overall_grade).to(equal("A"))
    expect(result.coverage_partial).to(be_false)


def test_cap_never_raises_a_grade_already_below_c() -> None:
    # build a D/E/F site, then assert partial coverage does NOT lift it to C.
    # 2 high/alta = 40 penalty -> web_score 60 -> grade D.
    findings = [
        make_finding(severity="high", confidence="alta", category="A01"),
        make_finding(severity="high", confidence="alta", category="A03"),
    ]
    result = compute_score(
        ScoreInput(
            findings=findings,
            agentic_status=AgenticStatus.NO_SURFACE,
            partial_coverage=True,
        )
    )

    expect(result.overall_score).to(equal(60))
    expect(result.overall_grade).to(equal("D"))  # cap to C does NOT lift D up


def test_cap_lowers_b_to_c_but_not_below() -> None:
    # 2 high/alta -> 40 penalty -> 60 (D). Use 1 high -> 20 penalty -> 80 (B).
    findings = [make_finding(severity="high", confidence="alta")]
    result = compute_score(
        ScoreInput(
            findings=findings,
            agentic_status=AgenticStatus.NO_SURFACE,
            partial_coverage=True,
        )
    )

    expect(result.web_score).to(equal(80))
    expect(result.overall_grade).to(equal("C"))  # B capped down to C


def test_cap_does_not_touch_penalty_or_dimension_grades() -> None:
    findings = [make_finding(severity="high", confidence="alta")]
    result = compute_score(
        ScoreInput(
            findings=findings,
            agentic_status=AgenticStatus.NO_SURFACE,
            partial_coverage=True,
        )
    )

    # penalty_raw untouched by the cap
    expect(result.penalty_raw).to(equal(20))
    # the per-dimension display grade ignores the cap: web_score 80 -> B
    expect(dimension_grade(result.web_score)).to(equal("B"))
