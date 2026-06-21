"""Scan presenters — domain ``Scan`` → camelCase API dicts (12-api).

``GET /scans/{id}`` exposes the score + observability columns **read-only**
straight from the ``scans`` row (07-scoring writes them; the API never recomputes).
The PK is surfaced as ``scanId`` (UUIDv4, non-enumerable) per the anti-IDOR rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.common.domain.interfaces.presenter import Presenter
from src.scans.domain.models.scan import Scan


@dataclass
class ScanCreatedPresenter(Presenter[Scan]):
    """Minimal body for ``POST /scans`` — just the id + state for 201/200."""

    instance: Scan

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "scanId": str(self.instance.uuid),
            "siteId": str(self.instance.site_id),
            "level": self.instance.level,
            "status": self.instance.status,
            "visibility": self.instance.visibility,
        }


@dataclass
class ScanListItemPresenter(Presenter[Scan]):
    """Row shape for ``GET /scans`` (list)."""

    instance: Scan

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "scanId": str(self.instance.uuid),
            "siteId": str(self.instance.site_id),
            "level": self.instance.level,
            "status": self.instance.status,
            "visibility": self.instance.visibility,
            "overallGrade": self.instance.overall_grade,
            "overallScore": self.instance.overall_score,
            "progress": self.instance.progress,
            "createdAt": self.instance.created_at,
            "finishedAt": self.instance.finished_at,
        }


@dataclass
class ScanDetailPresenter(Presenter[Scan]):
    """Full state + scores + observability for ``GET /scans/{id}``.

    ``host`` is the audited hostname, loaded from the ``sites`` row by the
    endpoint (the ``scans`` row only carries ``site_id``); the live-view/report
    render it as the title.
    """

    instance: Scan
    host: str | None = None

    @property
    def to_dict(self) -> dict[str, Any]:
        scan = self.instance
        return {
            "scanId": str(scan.uuid),
            "siteId": str(scan.site_id),
            "host": self.host,
            "level": scan.level,
            "status": scan.status,
            "visibility": scan.visibility,
            # Scoring (read-only, from the scans columns — owned by 07).
            "webScore": scan.web_score,
            "agenticScore": scan.agentic_score,
            "overallScore": scan.overall_score,
            "overallGrade": scan.overall_grade,
            "agenticStatus": scan.agentic_status,
            "penaltyRaw": scan.penalty_raw,
            # Observability / live-view on reload.
            "progress": scan.progress,
            "currentPhase": scan.current_phase,
            "toolsStatus": scan.tools_status,
            "coverage": scan.coverage,
            # True when the run degraded to partial coverage (a tool failed/timed
            # out) → grade capped at C; the UI shows a "cobertura parcial" badge.
            "partialCoverage": scan.status == "partial",
            "error": scan.error,
            "summary": scan.summary,
            "startedAt": scan.started_at,
            "finishedAt": scan.finished_at,
            "createdAt": scan.created_at,
            "updatedAt": scan.updated_at,
        }
