"""Enriched watchlist-row presenter — ``WatchlistRowView`` → camelCase (12-api).

Renders the row the watchlist UI consumes: row ``id`` (for PATCH/DELETE, never
``siteId``), the site ``host`` and the latest scan's grades. ``agenticStatus`` is
coerced to the client's coverage enum (``no_surface``/``detected_not_tested``/
``tested``) so backend-only states (e.g. ``error``) never break client parsing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.common.domain.interfaces.presenter import Presenter
from src.sites.application.services.watchlist_row import WatchlistRowView

# Coverage states the client understands; anything else degrades to "no_surface".
_AGENTIC_STATUS = {"no_surface", "detected_not_tested", "tested"}


@dataclass
class WatchlistRowPresenter(Presenter[WatchlistRowView]):
    instance: WatchlistRowView

    @property
    def to_dict(self) -> dict[str, Any]:
        row = self.instance
        status = row.agentic_status
        return {
            "id": str(row.id),
            "siteId": str(row.site_id),
            "host": row.hostname,
            "departmentName": None,
            "overallGrade": row.overall_grade,
            "webGrade": row.web_grade,
            "agenticGrade": row.agentic_grade,
            "agenticStatus": status if status in _AGENTIC_STATUS else "no_surface",
            "monitor": row.monitor,
            "lastScanAt": row.last_scan_at,
        }
