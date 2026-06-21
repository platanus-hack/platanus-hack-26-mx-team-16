"""Public-report presenter — redacted ``/r/{token}`` body (12-api §11.3 / 09).

Serves the executive layer + scores read from the ``scans`` row. Technical
findings are intentionally **not** included here at the API layer: the full
redacted render (exec summary + findings WITHOUT exploit payloads) is owned by
09-reporting, which will compose this with :class:`RedactedFindingPresenter`. The
shape stays minimal-but-safe so no raw exploit can leak through the public token.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.common.domain.interfaces.presenter import Presenter
from src.scans.application.use_cases.get_public_report import PublicReportView


@dataclass
class PublicReportPresenter(Presenter[PublicReportView]):
    instance: PublicReportView

    @property
    def to_dict(self) -> dict[str, Any]:
        scan = self.instance.scan
        return {
            "scanId": str(scan.uuid),
            "siteId": str(scan.site_id),
            "level": scan.level,
            "status": scan.status,
            # Executive scores (safe to expose publicly).
            "overallScore": scan.overall_score,
            "overallGrade": scan.overall_grade,
            "webScore": scan.web_score,
            "agenticScore": scan.agentic_score,
            "agenticStatus": scan.agentic_status,
            "coverage": scan.coverage,
            "summary": scan.summary,
            "finishedAt": scan.finished_at,
            # Findings are added by 09-reporting via RedactedFindingPresenter
            # (no raw exploit payloads ever cross the public token).
            "redacted": True,
        }
