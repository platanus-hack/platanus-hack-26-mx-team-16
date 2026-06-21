"""Leaderboard order + dedupe + version tests (07-scoring §6) — pure domain."""

from __future__ import annotations

from expects import contain, equal, expect, have_length

from src.common.domain.enums.scans import AgenticStatus
from src.scans.domain.services.scoring import (
    LEADERBOARD_ORDER,
    SCORING_VERSION,
    ScoreInput,
    ScoreResult,
    compute_score,
    dedupe,
    leaderboard_sort_key,
)
from tests.scans.domain._factories import make_finding


def _result(grade: str, penalty: int, score: int = 0) -> ScoreResult:
    return ScoreResult(
        web_score=score,
        agentic_score=None,
        overall_score=score,
        overall_grade=grade,
        penalty_raw=penalty,
        coverage_partial=False,
        agentic_detected_untested=False,
    )


def test_leaderboard_order_contract_is_grade_desc_penalty_desc() -> None:
    # Hall of Shame: worst-first -> grade DESC (F before A), penalty DESC tiebreak.
    expect(LEADERBOARD_ORDER).to(
        equal((("overall_grade", "DESC"), ("penalty_raw", "DESC")))
    )


def test_two_f_sites_tiebreak_by_penalty_desc() -> None:
    # both collapsed to F/0; worst (highest penalty_raw) sorts first
    low = _result("F", penalty=120)
    high = _result("F", penalty=480)
    mid = _result("F", penalty=200)

    ordered = sorted([low, high, mid], key=leaderboard_sort_key)

    expect([r.penalty_raw for r in ordered]).to(equal([480, 200, 120]))


def test_grade_dominates_penalty_in_order() -> None:
    a_site = _result("A", penalty=0, score=100)
    f_site = _result("F", penalty=500)
    c_site = _result("C", penalty=10, score=72)

    ordered = sorted([f_site, a_site, c_site], key=leaderboard_sort_key)

    # worst first means F is FIRST (grade DESC): F, then C, then A
    expect([r.overall_grade for r in ordered]).to(equal(["F", "C", "A"]))


def test_majority_gob_mx_collapse_to_f_at_zero() -> None:
    # 3 criticals/alta -> penalty 120 -> web_score 0 -> overall 0 -> grade F (not E)
    findings = [
        make_finding(severity="critical", confidence="alta", category=f"A{i:02d}")
        for i in range(1, 4)
    ]
    result = compute_score(
        ScoreInput(findings=findings, agentic_status=AgenticStatus.NO_SURFACE)
    )

    expect(result.overall_score).to(equal(0))
    expect(result.overall_grade).to(equal("F"))
    expect(result.penalty_raw).to(equal(120))


def test_dedupe_collapses_identical_findings() -> None:
    # same source/category/url/param/tool -> one dedupe_key -> collapsed to 1
    f = make_finding(severity="high", confidence="alta", category="A01")
    deduped = dedupe([f, f, f])

    expect(deduped).to(have_length(1))


def test_dedupe_runs_inside_compute_score() -> None:
    f = make_finding(severity="high", confidence="alta", category="A01")
    # three identical findings collapse to one -> penalty 20, not 60
    result = compute_score(
        ScoreInput(findings=[f, f, f], agentic_status=AgenticStatus.NO_SURFACE)
    )

    expect(result.penalty_raw).to(equal(20))
    expect(result.web_score).to(equal(80))


def test_collapse_by_category_keeps_worst_per_category_endpoint() -> None:
    # same category+endpoint, different severity -> only the worst counts when on
    findings = [
        make_finding(severity="low", confidence="alta", category="A01", endpoint="/x", param="a"),
        make_finding(severity="critical", confidence="alta", category="A01", endpoint="/x", param="b"),
    ]
    with_collapse = compute_score(
        ScoreInput(
            findings=findings,
            agentic_status=AgenticStatus.NO_SURFACE,
            collapse_by_category=True,
        )
    )
    without_collapse = compute_score(
        ScoreInput(
            findings=findings,
            agentic_status=AgenticStatus.NO_SURFACE,
            collapse_by_category=False,
        )
    )

    # collapse keeps only the critical (40); raw counts both (40 + 3 = 43)
    expect(with_collapse.penalty_raw).to(equal(40))
    expect(without_collapse.penalty_raw).to(equal(43))


def test_version_is_propagated() -> None:
    result = compute_score(
        ScoreInput(findings=[], agentic_status=AgenticStatus.NO_SURFACE)
    )

    expect(result.version).to(equal(SCORING_VERSION))


def test_score_result_field_names_match_scans_columns() -> None:
    # the worker writes these to scans.* — guard the shape (06-data-model)
    result = compute_score(
        ScoreInput(findings=[], agentic_status=AgenticStatus.NO_SURFACE)
    )
    fields = result.__dataclass_fields__.keys()

    for column in ("web_score", "agentic_score", "overall_score", "overall_grade", "penalty_raw"):
        expect(list(fields)).to(contain(column))
