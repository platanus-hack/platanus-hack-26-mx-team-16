"""Ranking-item presenter — leaderboard ``Scan`` → camelCase (12-api §"Lectura").

Each row is a gov site's latest public scan, worst-first
(``overall_grade ASC, penalty_raw DESC`` — 07-scoring's ``LEADERBOARD_ORDER``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.common.domain.interfaces.presenter import Presenter
from src.scans.domain.models.scan import Scan


@dataclass
class RankingItemPresenter(Presenter[Scan]):
    instance: Scan

    @property
    def to_dict(self) -> dict[str, Any]:
        scan = self.instance
        return {
            "scanId": str(scan.uuid),
            "siteId": str(scan.site_id),
            "overallGrade": scan.overall_grade,
            "overallScore": scan.overall_score,
            "webScore": scan.web_score,
            "agenticScore": scan.agentic_score,
            "penaltyRaw": scan.penalty_raw,
            "finishedAt": scan.finished_at,
        }
