"""Pure-domain tests for grade comparison + new-critical filtering
(08-ranking-watchlists §4.2/§4.3). No I/O."""

from uuid import uuid4

from expects import be_false, be_true, equal, expect

from src.scans.domain.models.finding import FindingRecord
from src.scans.domain.services.grade_delta import (
    compare_grade,
    grade_rank,
    new_criticals,
)


def _finding(*, severity: str, dedupe_key: str) -> FindingRecord:
    return FindingRecord(
        uuid=uuid4(),
        scan_id=uuid4(),
        site_id=uuid4(),
        source="owasp",
        tool="nuclei",
        category="A05",
        title="x",
        severity=severity,
        confidence="alta",
        description="d",
        impact="i",
        remediation="r",
        status="open",
        dedupe_key=dedupe_key,
    )


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


def test_new_criticals_only_new_keys_and_critical_severity():
    new_key = "key-new"
    old_key = "key-old"
    findings = [
        _finding(severity="critical", dedupe_key=new_key),
        _finding(severity="critical", dedupe_key=old_key),  # pre-existing
        _finding(severity="high", dedupe_key="key-high-new"),  # not critical
    ]
    result = new_criticals(findings, scan_first_seen_keys={new_key, "key-high-new"})

    expect(len(result)).to(equal(1))
    expect(result[0].dedupe_key).to(equal(new_key))
