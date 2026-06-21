"""Assemble enriched watchlist rows (12-api §"Watchlist").

A watchlist row the UI can render needs more than the bare ``WatchlistEntry``
(row uuid + ``site_id`` + ``monitor``): it shows the site ``hostname`` and the
grades of the site's latest scan ("🛡️ web / 🤖 agéntico / global"). This service
joins those three sources — the entry, its ``Site`` and the site's
``latest_scan_id`` scan — into a single read-model, mirroring how the gov ranking
surfaces a site's latest-scan grades. Per-dimension grades are display-only,
derived from the scan's scores via ``dimension_grade`` (07-scoring §5.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.scans.domain.repositories.scan import ScanRepository
from src.scans.domain.services.scoring import dimension_grade
from src.sites.domain.models.site import Site
from src.sites.domain.models.watchlist import WatchlistEntry
from src.sites.domain.repositories.site import SiteRepository


@dataclass
class WatchlistRowView:
    """Enriched watchlist row: the entry plus its site + latest-scan grades."""

    id: UUID
    site_id: UUID
    hostname: str
    monitor: bool
    overall_grade: str | None
    web_grade: str | None
    agentic_grade: str | None
    agentic_status: str | None
    last_scan_at: datetime | None


async def build_watchlist_row(
    entry: WatchlistEntry,
    *,
    site_repository: SiteRepository,
    scan_repository: ScanRepository,
    site: Site | None = None,
) -> WatchlistRowView:
    """Join ``entry`` with its site and the site's latest scan into a row view.

    ``site`` may be passed in when the caller already resolved it (e.g. the add
    flow's ``get_or_create``) to skip a redundant lookup. A site with no scan yet
    yields ``None`` grades — the UI renders that as "Nunca escaneado".
    """
    if site is None:
        site = await site_repository.find(entry.site_id)

    scan = (
        await scan_repository.find(site.latest_scan_id)
        if site and site.latest_scan_id
        else None
    )

    return WatchlistRowView(
        id=entry.uuid,
        site_id=entry.site_id,
        hostname=site.hostname if site else "",
        monitor=entry.monitor,
        overall_grade=scan.overall_grade if scan else None,
        web_grade=(
            dimension_grade(scan.web_score)
            if scan and scan.web_score is not None
            else None
        ),
        agentic_grade=(
            dimension_grade(scan.agentic_score)
            if scan and scan.agentic_score is not None
            else None
        ),
        agentic_status=scan.agentic_status if scan else None,
        last_scan_at=scan.finished_at if scan else None,
    )
