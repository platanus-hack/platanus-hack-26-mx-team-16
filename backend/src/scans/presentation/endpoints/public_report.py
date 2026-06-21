"""``GET /r/{token}`` — public redacted report (12-api §"Reporte público").

Public (no auth). Token contract: unknown → 404, expired/revoked → 410,
valid → redacted report. The 404/410 split is raised inside ``GetPublicReport``.
"""

from __future__ import annotations

from fastapi import status

from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.scans.application.use_cases.get_public_report import GetPublicReport
from src.scans.presentation.presenters.public_report import PublicReportPresenter


async def get_public_report(
    token: str,
    domain_context: DomainContextDep,
) -> ApiJSONResponse:
    view = await GetPublicReport(
        token=token,
        public_report_repository=domain_context.public_report_repository,
        scan_repository=domain_context.scan_repository,
    ).execute()

    return ApiJSONResponse(
        content=PublicReportPresenter(view).to_dict,
        status_code=status.HTTP_200_OK,
    )
