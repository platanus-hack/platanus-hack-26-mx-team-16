"""Site-history presenter — ``SiteHistoryView`` → camelCase (12-api §"Lectura")."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.common.domain.interfaces.presenter import Presenter
from src.scans.presentation.presenters.scan import ScanListItemPresenter
from src.sites.application.use_cases.get_site_history import SiteHistoryView


@dataclass
class SiteHistoryPresenter(Presenter[SiteHistoryView]):
    instance: SiteHistoryView

    @property
    def to_dict(self) -> dict[str, Any]:
        view = self.instance
        site = view.site
        return {
            "siteId": str(site.uuid),
            "url": site.url,
            "hostname": site.hostname,
            "isGov": site.is_gov,
            "country": site.country,
            "latestScan": (
                ScanListItemPresenter(view.latest_scan).to_dict
                if view.latest_scan
                else None
            ),
            "history": [
                ScanListItemPresenter(scan).to_dict for scan in view.history
            ],
        }
