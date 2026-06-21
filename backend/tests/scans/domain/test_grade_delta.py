"""Pure-domain tests for grade comparison (08-ranking-watchlists §4.2/§4.3).

New-critical detection lives in ``FindingRepository.criticals_first_seen_in``
(the single source of truth) and is covered by the repository tests, not here.
No I/O."""

from expects import be_false, be_true, equal, expect

from src.scans.domain.services.grade_delta import compare_grade, grade_rank


def test_compare_grade_true_only_when_worse():
    expect(compare_grade("B", "D")).to(be_true)
    expect(compare_grade("A", "F")).to(be_true)
    expect(compare_grade("B", "A")).to(be_false)  # improved
    expect(compare_grade("B", "B")).to(be_false)  # same


def test_compare_grade_missing_base_is_false():
    expect(compare_grade(None, "F")).to(be_false)  # first scan, no base
    expect(compare_grade("C", None)).to(be_false)


def test_grade_rank_f_is_worst():
    expect(grade_rank("F")).to(equal(5))
    expect(grade_rank("A")).to(equal(0))
    expect(grade_rank("f")).to(equal(5))  # case-insensitive
    expect(grade_rank(None)).to(equal(None))
