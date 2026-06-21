"""``GET /scans/{id}`` — status + scores + observability (12-api §"Lectura").

Access control (404 for private non-owner) is enforced by ``require_scan_access``,
which resolves and returns the authorized ``Scan``. The site is loaded for its
``hostname`` so the live-view/report can render the audited host (the ``scans``
row only carries ``site_id``).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, status

from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.ownership import require_scan_access
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.scans.domain.models.scan import Scan
from src.scans.presentation.presenters.scan import ScanDetailPresenter


async def get_scan(
    scan: Annotated[Scan, Depends(require_scan_access)],
    domain_context: DomainContextDep,
) -> ApiJSONResponse:
    site = await domain_context.site_repository.find(scan.site_id)
    return ApiJSONResponse(
        content=ScanDetailPresenter(
            scan, host=site.hostname if site is not None else None
        ).to_dict,
        status_code=status.HTTP_200_OK,
    )
