"""``POST /scans/{id}/cancel`` — kill a hung scan (12-api §"Cancelación").

``require_scan_owner`` enforces owner-only (404 otherwise) and resolves the scan.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, status

from src.common.infrastructure.dependencies.common import (
    DomainContextDep,
    RedisClientDep,
)
from src.common.infrastructure.dependencies.ownership import require_scan_owner
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.scans.application.use_cases.cancel_scan import CancelScan
from src.scans.domain.models.scan import Scan
from src.scans.presentation.presenters.scan import ScanDetailPresenter


async def cancel_scan(
    domain_context: DomainContextDep,
    redis_client: RedisClientDep,
    scan: Annotated[Scan, Depends(require_scan_owner)],
) -> ApiJSONResponse:
    cancelled = await CancelScan(
        scan=scan,
        scan_repository=domain_context.scan_repository,
        scan_event_repository=domain_context.scan_event_repository,
        redis_client=redis_client,
    ).execute()

    return ApiJSONResponse(
        content=ScanDetailPresenter(cancelled).to_dict,
        status_code=status.HTTP_200_OK,
    )
