"""``POST /scans/{id}/share`` — mint a public report link (12-api §"Reporte público").

Owner-only via ``require_scan_owner`` (404 otherwise). Returns the token + URL.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, status

from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.ownership import require_scan_owner
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.scans.application.use_cases.create_public_share import CreatePublicShare
from src.scans.domain.models.scan import Scan
from src.scans.presentation.presenters.share import ShareTokenPresenter
from src.scans.presentation.requests.share_scan import ShareScanRequest


async def share_scan(
    domain_context: DomainContextDep,
    scan: Annotated[Scan, Depends(require_scan_owner)],
    request: ShareScanRequest | None = None,
) -> ApiJSONResponse:
    ttl_days = request.ttl_days if request is not None else None
    report = await CreatePublicShare(
        scan=scan,
        public_report_repository=domain_context.public_report_repository,
        ttl_days=ttl_days,
    ).execute()

    return ApiJSONResponse(
        content=ShareTokenPresenter(report).to_dict,
        status_code=status.HTTP_201_CREATED,
    )
