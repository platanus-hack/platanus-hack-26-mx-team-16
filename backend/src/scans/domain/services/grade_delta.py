"""Pure grade-comparison + new-critical extraction for monitoring alerts
(08-ranking-watchlists §4.2/§4.3).

This module never recomputes a grade or a score — scoring (07) already wrote
``overall_grade``. It only compares two already-written ``char(1)`` grades and
filters findings that are *new* at the site level. No I/O, no repos.
"""

from __future__ import annotations

from src.scans.domain.models.finding import FindingRecord

# Worst-first ordering: F is the worst grade, A the best. A site's grade
# "dropped" when it moved to a worse grade between two consecutive scans.
_GRADE_RANK = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}

_CRITICAL = "critical"


def grade_rank(grade: str | None) -> int | None:
    """Map a grade letter to its worst-first rank (A=0 … F=5). ``None`` for an
    unknown/absent grade (no comparison base)."""
    if grade is None:
        return None
    return _GRADE_RANK.get(grade.strip().upper())


def compare_grade(prev: str | None, curr: str | None) -> bool:
    """Return ``True`` iff the grade **worsened** from ``prev`` to ``curr``.

    B→D ⇒ True; B→A (improved) ⇒ False; B→B (same) ⇒ False. If either grade is
    missing (e.g. the first scan of a site, or a non-graded scan) there is no
    comparison base ⇒ False (never alert on a drop).
    """
    prev_rank = grade_rank(prev)
    curr_rank = grade_rank(curr)
    if prev_rank is None or curr_rank is None:
        return False
    return curr_rank > prev_rank


def new_criticals(
    findings: list[FindingRecord], *, scan_first_seen_keys: set[str]
) -> list[FindingRecord]:
    """Filter ``findings`` to the **new critical** ones for this scan.

    A finding is a *new critical* when its severity is ``critical`` and its
    ``dedupe_key`` is in ``scan_first_seen_keys`` — the set of dedupe keys whose
    ``first_seen`` corresponds to this scan (i.e. they did not exist in the
    site's history before). A critical that already existed (older ``first_seen``)
    is excluded, so repeat cycles never re-alert on the same finding (§5.2).
    """
    return [
        finding
        for finding in findings
        if finding.severity == _CRITICAL
        and finding.dedupe_key in scan_first_seen_keys
    ]
