"""Penalty / sub-score formula tests (07-scoring §2/§3) — pure domain."""

from __future__ import annotations

import pytest
from expects import be_none, equal, expect

from src.common.domain.enums.scans import AgenticStatus
from src.scans.domain.services.scoring import (
    ScoreInput,
    _penalty_raw,
    _sub_score,
    compute_score,
)
from tests.scans.domain._factories import make_finding


@pytest.mark.parametrize(
    ("severity", "confidence", "expected"),
    [
        ("critical", "alta", 40),  # 40 * 1.0
        ("high", "alta", 20),  # 20 * 1.0
        ("medium", "media", 6),  # 8 * 0.7 = 5.6 -> round = 6
        ("low", "baja", 1),  # 3 * 0.4 = 1.2 -> round = 1
        ("medium", "baja", 3),  # 8 * 0.4 = 3.2 -> round = 3
        ("info", "alta", 0),  # info weighs 0
        ("info", "baja", 0),
    ],
)
def test_single_finding_penalty(severity: str, confidence: str, expected: int) -> None:
    penalty = _penalty_raw([make_finding(severity=severity, confidence=confidence)])

    expect(penalty).to(equal(expected))


def test_penalty_rounds_the_sum_not_per_term() -> None:
    # two medium/media = 5.6 + 5.6 = 11.2 -> round = 11 (not 6 + 6 = 12)
    findings = [
        make_finding(severity="medium", confidence="media", category="A01"),
        make_finding(severity="medium", confidence="media", category="A03"),
    ]

    expect(_penalty_raw(findings)).to(equal(11))


def test_info_findings_do_not_move_penalty_or_score() -> None:
    findings = [
        make_finding(severity="high", confidence="alta", category="A01"),
        make_finding(severity="info", confidence="alta", category="A05"),
        make_finding(severity="info", confidence="baja", category="A06"),
    ]

    result = compute_score(
        ScoreInput(findings=findings, agentic_status=AgenticStatus.NO_SURFACE)
    )

    # only the single high counts: penalty 20, score 80
    expect(result.penalty_raw).to(equal(20))
    expect(result.web_score).to(equal(80))


def test_penalty_raw_is_uncapped_while_subscore_clamps_to_zero() -> None:
    # 5 criticals/alta = 200 penalty; web_score floors at 0 but penalty_raw stays 200
    findings = [
        make_finding(severity="critical", confidence="alta", category=f"A{i:02d}")
        for i in range(1, 6)
    ]

    result = compute_score(
        ScoreInput(findings=findings, agentic_status=AgenticStatus.NO_SURFACE)
    )

    expect(result.penalty_raw).to(equal(200))
    expect(result.web_score).to(equal(0))
    expect(result.overall_score).to(equal(0))
    expect(result.overall_grade).to(equal("F"))


@pytest.mark.parametrize(
    ("penalty", "expected"),
    [(0, 100), (20, 80), (100, 0), (150, 0), (1, 99)],
)
def test_sub_score_clamps_to_0_100(penalty: int, expected: int) -> None:
    expect(_sub_score(penalty)).to(equal(expected))


def test_no_findings_is_perfect_web_score() -> None:
    result = compute_score(
        ScoreInput(findings=[], agentic_status=AgenticStatus.NO_SURFACE)
    )

    expect(result.web_score).to(equal(100))
    expect(result.penalty_raw).to(equal(0))
    expect(result.overall_grade).to(equal("A"))
    expect(result.agentic_score).to(be_none)
