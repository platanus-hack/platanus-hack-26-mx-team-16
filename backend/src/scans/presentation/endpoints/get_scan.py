"""``GET /scans/{id}`` — status + scores + observability (12-api §"Lectura").

Access control (404 for private non-owner) is enforced by ``require_scan_access``,
which resolves and returns the authorized ``Scan``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, status

from src.common.infrastructure.dependencies.ownership import require_scan_access
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.scans.domain.models.scan import Scan
from src.scans.presentation.presenters.scan import ScanDetailPresenter


async def get_scan(
    scan: Annotated[Scan, Depends(require_scan_access)],
) -> ApiJSONResponse:
    return ApiJSONResponse(
        content=ScanDetailPresenter(scan).to_dict,
        status_code=status.HTTP_200_OK,
    )
