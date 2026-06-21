"""``GET /scans/{id}/findings`` — findings paginated by severity desc (12-api).

``require_scan_access`` enforces the 404-for-private-non-owner rule and resolves
the scan; we then page its findings.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query, status

from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.ownership import require_scan_access
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.scans.application.use_cases.list_scan_findings import ListScanFindings
from src.scans.domain.models.scan import Scan
from src.scans.presentation.presenters.finding import FindingPresenter


async def list_findings(
    domain_context: DomainContextDep,
    scan: Annotated[Scan, Depends(require_scan_access)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query()] = None,
) -> ApiJSONResponse:
    page = await ListScanFindings(
        scan_id=scan.uuid,
        finding_repository=domain_context.finding_repository,
        limit=limit,
        cursor=cursor,
    ).execute()

    page.apply_presenter(FindingPresenter)
    return ApiJSONResponse(content=page, status_code=status.HTTP_200_OK)
