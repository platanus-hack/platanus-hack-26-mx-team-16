"""Curated, versioned scoring weight table (07-scoring §2/§5).

A single audited constant module: severity penalties, confidence factors, grade
bands and the partial-coverage cap. Indexed by the frozen enums in
``src/common/domain/enums/scans.py`` (07-scoring plan §2.1) so the curve is
type-checked rather than stringly-typed.

``SCORING_VERSION`` freezes the curve: any change to a weight or band MUST bump
it, which deliberately breaks the boundary tests in ``tests/scans/domain`` and
forces a conscious review. The algorithm that consumes this table lives in
``scoring.py``; nothing here does I/O.
"""

from __future__ import annotations

from src.common.domain.enums.scans import FindingConfidence, FindingSeverity

# Bump deliberately when the curve changes (07-scoring plan §2.1). A bump breaks
# the boundary tests on purpose -> conscious review of any weight/band change.
SCORING_VERSION = "1"

# Severity penalty (spec §2). ``info`` weighs 0 and NEVER moves the score (§3) —
# this includes the meta findings the engine emits ("tool X did not complete",
# "cobertura incompleta").
SEVERITY_PENALTY: dict[FindingSeverity, int] = {
    FindingSeverity.CRITICAL: 40,
    FindingSeverity.HIGH: 20,
    FindingSeverity.MEDIUM: 8,
    FindingSeverity.LOW: 3,
    FindingSeverity.INFO: 0,
}

# Confidence factor (spec §2).
CONFIDENCE_FACTOR: dict[FindingConfidence, float] = {
    FindingConfidence.ALTA: 1.0,
    FindingConfidence.MEDIA: 0.7,
    FindingConfidence.BAJA: 0.4,
}

# Grade bands over ``overall_score`` (spec §5.1). DESC order; the first band whose
# threshold is ``<= score`` wins. The ``E`` step (40–59) opens resolution in the
# crowded gov leaderboard zone where many real ``.gob.mx`` sites land.
GRADE_BANDS: tuple[tuple[int, str], ...] = (
    (90, "A"),
    (80, "B"),
    (70, "C"),
    (60, "D"),
    (40, "E"),
    (0, "F"),
)

# Max ``overall_grade`` when ``scans.status='partial'`` (spec §4 / §5.2). A site
# that crashes a base scanner can never come out A/B.
PARTIAL_COVERAGE_CAP = "C"
