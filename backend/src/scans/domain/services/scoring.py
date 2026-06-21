"""Deterministic scoring service (07-scoring §2–§6) — pure domain logic.

Takes already-deduplicated ``list[Finding]`` + ``agentic_status`` +
``partial_coverage`` and returns a frozen ``ScoreResult`` (``web_score``,
``agentic_score``, ``overall_score``, ``overall_grade``, ``penalty_raw``). It is
the spec formula translated to table-driven Python over ``scoring_weights``.

NO I/O, NO DB, NO LLM. The worker (05-agent-team) builds the ``ScoreInput`` after
parsing + dedupe and persists the ``ScoreResult`` via ``SQLScanRepository`` (06).
The LLM never computes the score — it only narrates from the numbered summary.

Leaderboard order is owned here: ``LEADERBOARD_ORDER`` documents the authoritative
worst-first ``(overall_grade DESC, penalty_raw DESC)`` contract, and
``leaderboard_sort_key`` is the drop-in Python sort key for it (consumed by 08/12/13).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from src.common.domain.enums.scans import (
    AgenticStatus,
    FindingConfidence,
    FindingSeverity,
    FindingSource,
)
from src.scans.domain.contracts.finding import Finding
from src.scans.domain.services.dedupe import compute_dedupe_key
from src.scans.domain.services.scoring_weights import (
    CONFIDENCE_FACTOR,
    GRADE_BANDS,
    PARTIAL_COVERAGE_CAP,
    SCORING_VERSION,
    SEVERITY_PENALTY,
)

# Re-exported so consumers (08/12/13, tests) get the frozen curve version from
# the scoring entry point without reaching into scoring_weights.
__all__ = [
    "LEADERBOARD_ORDER",
    "SCORING_VERSION",
    "ScoreInput",
    "ScoreResult",
    "compute_score",
    "dedupe",
    "dimension_grade",
    "leaderboard_sort_key",
]

# Authoritative leaderboard order contract (07-scoring §6). The SINGLE source of
# truth for "worst first" (the gov leaderboard): grade DESCENDING so the worst
# letter leads (F before ... before A), then raw penalty descending to break ties
# when dozens of ``.gob.mx`` collapse to F (penalty 300 before 120).
# 08-ranking-watchlists / 12-api / 13-frontend MUST cite this exact tuple; the SQL
# ``leaderboard()`` mirrors it as ``ORDER BY overall_grade DESC, penalty_raw DESC``.
# NOTE: the 07 spec prose's "(... ASC ...)" notation was a slip — the product
# intent and these tests are worst-first; this DESC tuple is authoritative.
LEADERBOARD_ORDER: tuple[tuple[str, str], ...] = (
    ("overall_grade", "DESC"),
    ("penalty_raw", "DESC"),
)

# Rank for ``_apply_caps``: lower index == better grade. Used to compare the
# numeric grade against the partial-coverage cap without string fiddling.
_GRADE_RANK: dict[str, int] = {grade: idx for idx, (_, grade) in enumerate(GRADE_BANDS)}


@dataclass(frozen=True)
class ScoreInput:
    """Frozen input to ``compute_score`` (07-scoring plan §2.2).

    ``findings`` are already deduplicated by ``dedupe_key`` (06 §3.3) before they
    reach scoring; ``compute_score`` re-collapses defensively (see ``dedupe``).
    ``partial_coverage`` is the boolean the caller derives from the ``coverage``
    jsonb (``any(t.status != 'ok')``) — the service never reads the raw jsonb,
    keeping the domain pure.
    """

    findings: list[Finding]
    agentic_status: AgenticStatus
    partial_coverage: bool = False
    # Optional anti-inflation (spec §2 note): count only the worst finding per
    # ``(category, endpoint)``. Off by default to match the raw demo count.
    collapse_by_category: bool = False


@dataclass(frozen=True)
class ScoreResult:
    """Frozen scoring output — the shape the worker writes to ``scans.*`` (06).

    ``penalty_raw`` is UNCAPPED (web/OWASP driver of the leaderboard tie-break,
    §6). ``agentic_score`` is ``None`` for ``no_surface`` / ``detected_not_tested``.
    ``agentic_detected_untested`` carries the "IA detectada, sin auditar" badge
    so the report distinguishes it from ``no_surface`` without re-reading status.
    """

    web_score: int
    agentic_score: int | None
    overall_score: int
    overall_grade: str
    penalty_raw: int
    coverage_partial: bool
    agentic_detected_untested: bool
    version: str = SCORING_VERSION


def dedupe(findings: Iterable[Finding]) -> list[Finding]:
    """Collapse duplicate findings, keeping first occurrence per identity.

    Reuses ``compute_dedupe_key`` (06 §3.3) for keying — does NOT reinvent the
    hash. ``Finding`` carries no ``site_id`` (it is the scan-scoped contract), so
    a constant placeholder is used: dedupe here is relative within one scan's
    finding list, which is exactly what scoring needs before summing penalties.
    """
    seen: set[str] = set()
    out: list[Finding] = []
    for f in findings:
        key = compute_dedupe_key(
            site_id="",  # scan-relative dedupe; identity within one finding list
            source=f.source,
            category=f.category,
            affected_url=f.affected_url,
            param=f.param,
            tool=f.tool,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def _collapse_by_category(findings: list[Finding]) -> list[Finding]:
    """Keep only the worst finding per ``(category, endpoint)`` (spec §2 note).

    "Worst" == highest severity penalty, tie-broken by confidence factor. Anti-
    inflation knob, independent of ``dedupe_key`` collapsing which runs first.
    """
    best: dict[tuple[str, str | None], Finding] = {}
    for f in findings:
        key = (f.category, f.endpoint)
        current = best.get(key)
        if current is None or _finding_weight(f) > _finding_weight(current):
            best[key] = f
    return list(best.values())


def _finding_weight(f: Finding) -> float:
    """Penalty contribution of a single finding: severity penalty × conf factor."""
    severity = FindingSeverity(f.severity)
    confidence = FindingConfidence(f.confidence)
    return SEVERITY_PENALTY[severity] * CONFIDENCE_FACTOR[confidence]


def _penalty_raw(findings: list[Finding]) -> int:
    """Σ severity_penalty × confidence_factor over findings — UNCAPPED (spec §2).

    ``info`` (weight 0) contributes 0 and never moves the score (§3). Rounds the
    final sum, not per term.
    """
    total = sum(_finding_weight(f) for f in findings)
    return round(total)


def _sub_score(penalty_raw: int) -> int:
    """Project an (uncapped) penalty to a displayable 0–100 sub-score (spec §2).

    The ``min(100, …)`` cap applies ONLY here, never to the persisted
    ``penalty_raw`` that orders the leaderboard.
    """
    return max(0, 100 - min(100, penalty_raw))


def _grade_for(score: int) -> str:
    """First DESC band whose threshold ``<= score`` (spec §5.1)."""
    for threshold, grade in GRADE_BANDS:
        if score >= threshold:
            return grade
    return GRADE_BANDS[-1][1]  # F (unreachable; the 0-band always matches)


def dimension_grade(score: int) -> str:
    """Display-only per-dimension letter grade (spec §5.1).

    Applies the SAME bands to ``web_score`` / ``agentic_score`` to render the
    star contrast ("🛡️ C web / 🤖 F agéntico"). NOT persisted, NOT in leaderboard
    order, NEVER substitutes ``overall_grade``; caps (§4) do not touch it.
    """
    return _grade_for(score)


def _apply_caps(grade: str, *, partial: bool) -> str:
    """Degrade ``overall_grade`` to the partial-coverage cap if needed (spec §4/§5.2).

    Only lowers the grade — a grade already at/below the cap is untouched. Never
    raises a grade.
    """
    if not partial:
        return grade
    cap_rank = _GRADE_RANK[PARTIAL_COVERAGE_CAP]
    if _GRADE_RANK[grade] < cap_rank:  # numeric grade is better than the cap
        return PARTIAL_COVERAGE_CAP
    return grade


def compute_score(inp: ScoreInput) -> ScoreResult:
    """Deterministic scoring pipeline (07-scoring §2–§6). The only public entry.

    1. dedupe (defensive) + optional category collapse.
    2. partition by ``source`` -> web (owasp) / agentic.
    3. ``penalty_raw`` (uncapped) -> ``web_score`` / ``agentic_score``.
    4. modulate by ``agentic_status`` -> ``overall_score``.
    5. derive ``overall_grade``; apply the partial-coverage cap.
    """
    findings = dedupe(inp.findings)
    if inp.collapse_by_category:
        findings = _collapse_by_category(findings)

    web = [f for f in findings if f.source == FindingSource.OWASP.value]
    agentic = [f for f in findings if f.source == FindingSource.AGENTIC.value]

    web_penalty_raw = _penalty_raw(web)
    web_score = _sub_score(web_penalty_raw)

    status = inp.agentic_status
    agentic_detected_untested = status == AgenticStatus.DETECTED_NOT_TESTED

    if status == AgenticStatus.TESTED:
        agentic_score: int | None = _sub_score(_penalty_raw(agentic))
        overall_score = round(0.6 * web_score + 0.4 * agentic_score)
    else:
        # no_surface and detected_not_tested both leave overall == web_score and
        # agentic_score None. detected_not_tested additionally raises the badge
        # flag — it is NEVER averaged and NEVER rewarded with 100.
        agentic_score = None
        overall_score = web_score

    grade = _apply_caps(_grade_for(overall_score), partial=inp.partial_coverage)

    # Persisted penalty_raw is the WEB driver (leaderboard tie-break, §6 / §8.4).
    return ScoreResult(
        web_score=web_score,
        agentic_score=agentic_score,
        overall_score=overall_score,
        overall_grade=grade,
        penalty_raw=web_penalty_raw,
        coverage_partial=inp.partial_coverage,
        agentic_detected_untested=agentic_detected_untested,
        version=SCORING_VERSION,
    )


def leaderboard_sort_key(result: ScoreResult) -> tuple[list[int], int]:
    """Python sort key implementing ``LEADERBOARD_ORDER`` (spec §6).

    Use as ``sorted(results, key=leaderboard_sort_key)`` for "worst first":
    grade DESCENDING (F before ... before A) then ``penalty_raw`` descending.
    Both fields are negated so a plain ascending ``sorted`` yields worst-first —
    the grade key negates each letter's ordinal so 'F' sorts ahead of 'A'.
    The authoritative order for any in-memory leaderboard; the SQL ``ORDER BY``
    in 08 mirrors the same tuple (``overall_grade DESC, penalty_raw DESC``).
    """
    return ([-ord(c) for c in result.overall_grade], -result.penalty_raw)
