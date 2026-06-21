"""``GET /scans/{id}/report`` — the in-app JSON report (12-api §"Lectura" / §F7).

The authenticated "Owliver te explica" screen (an RSC) renders the flat
``reportSchema`` DTO (exec synthesis + agentic inventory + technical findings).
This is the **JSON** sibling of ``report.pdf`` (PDF) and ``/r/{token}`` (public,
redacted): same persisted data, the owner sees full ``evidence``.

Access control (404 for a private non-owner) is enforced by ``require_scan_access``,
exactly like ``GET /scans/{id}`` — the backend never confirms a private scan's
existence. The host is loaded from the ``sites`` row (the ``scans`` row only
carries ``site_id``) and findings from the finding repository; assembly is
read-only (07 owns scoring, 05 owns the Opus summary).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, status

from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.ownership import require_scan_access
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.scans.domain.models.scan import Scan
from src.scans.presentation.presenters.report_view import ReportViewPresenter


async def get_report(
    scan: Annotated[Scan, Depends(require_scan_access)],
    domain_context: DomainContextDep,
) -> ApiJSONResponse:
    site = await domain_context.site_repository.find(scan.site_id)
    findings = await domain_context.finding_repository.list_for_scan(scan.uuid)
    return ApiJSONResponse(
        content=ReportViewPresenter(
            scan,
            host=site.hostname if site is not None else None,
            findings=findings,
        ).to_dict,
        status_code=status.HTTP_200_OK,
    )
