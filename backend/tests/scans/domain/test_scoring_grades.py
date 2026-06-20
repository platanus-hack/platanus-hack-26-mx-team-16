"""Grade-band boundary tests (07-scoring §5.1) — pure domain, table-driven."""

from __future__ import annotations

import pytest
from expects import equal, expect

from src.scans.domain.services.scoring import _grade_for, dimension_grade


@pytest.mark.parametrize(
    ("score", "grade"),
    [
        (100, "A"),
        (90, "A"),
        (89, "B"),
        (80, "B"),
        (79, "C"),
        (70, "C"),
        (69, "D"),
        (60, "D"),
        (59, "E"),
        (40, "E"),
        (39, "F"),
        (1, "F"),
        (0, "F"),
    ],
)
def test_grade_band_boundaries(score: int, grade: str) -> None:
    expect(_grade_for(score)).to(equal(grade))


@pytest.mark.parametrize("score", [40, 41, 50, 59])
def test_e_band_exists_in_40_to_59(score: int) -> None:
    expect(_grade_for(score)).to(equal("E"))


def test_zero_is_f_not_e() -> None:
    # the E step never rescues a collapsed site (07-scoring §5/§6).
    expect(_grade_for(0)).to(equal("F"))


@pytest.mark.parametrize(
    ("score", "grade"),
    [(72, "C"), (24, "F"), (95, "A"), (45, "E")],
)
def test_dimension_grade_uses_same_bands(score: int, grade: str) -> None:
    # display-only per-dimension grade reuses the overall bands (🛡️ web / 🤖 agentic)
    expect(dimension_grade(score)).to(equal(grade))
