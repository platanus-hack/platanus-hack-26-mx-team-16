"""``GetSiteHistory`` — ``GET /sites/{id}`` (12-api §"Lectura").

Returns the site plus its latest scan and the user-visible scan history. Private
scans of the site are filtered to the caller (owner or watcher); public scans are
always visible. Findings/score detail are read from the scan columns by the
presenter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from src.common.domain.enums.scans import ScanVisibility
from src.common.domain.interfaces.use_case import UseCase
from src.scans.domain.models.scan import Scan
from src.scans.domain.repositories.scan import ScanRepository
from src.sites.domain.models.site import Site
from src.sites.domain.repositories.site import SiteRepository
from src.sites.presentation.exceptions import SiteNotFoundError


@dataclass
class SiteHistoryView:
    site: Site
    latest_scan: Scan | None
    history: list[Scan] = field(default_factory=list)


@dataclass
class GetSiteHistory(UseCase):
    site_id: UUID
    site_repository: SiteRepository
    scan_repository: ScanRepository
    requester_id: UUID | None = None

    async def execute(self, *args, **kwargs) -> SiteHistoryView:
        site = await self.site_repository.find(self.site_id)
        if site is None:
            raise SiteNotFoundError

        latest_scan: Scan | None = None
        if site.latest_scan_id is not None:
            candidate = await self.scan_repository.find(site.latest_scan_id)
            if candidate is not None and self._can_view(candidate):
                latest_scan = candidate

        history = [latest_scan] if latest_scan is not None else []
        return SiteHistoryView(site=site, latest_scan=latest_scan, history=history)

    def _can_view(self, scan: Scan) -> bool:
        if scan.visibility == str(ScanVisibility.PUBLIC):
            return True
        return (
            self.requester_id is not None
            and scan.requested_by == self.requester_id
        )
