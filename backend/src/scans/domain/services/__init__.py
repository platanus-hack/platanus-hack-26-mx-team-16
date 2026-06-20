"""Pure scan-domain services (dedupe, scoring)."""

from src.scans.domain.services.scoring import (
    LEADERBOARD_ORDER,
    ScoreInput,
    ScoreResult,
    compute_score,
    dedupe,
    dimension_grade,
    leaderboard_sort_key,
)

__all__ = [
    "LEADERBOARD_ORDER",
    "ScoreInput",
    "ScoreResult",
    "compute_score",
    "dedupe",
    "dimension_grade",
    "leaderboard_sort_key",
]
