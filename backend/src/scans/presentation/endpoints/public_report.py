"""``GET /r/{token}`` — public redacted report (12-api §"Reporte público").

Public (no auth). Token contract: unknown → 404, expired/revoked → 410,
valid → redacted report. The 404/410 split is raised inside ``GetPublicReport``.

09-reporting fills the body: the full executive layer (grade, sub-scores, Opus
narrative, top-3, agentic inventory, badges) + the technical layer with each
finding's raw exploit **redacted** (``evidence: None`` + ``evidenceRedacted``).
A public link must never ship a reproducible attack against the user's own site
(spec §5). Redaction is enforced by :class:`PublicReportPresenter`, which pins
``public=True`` so it can never be skipped.
"""

from __future__ import annotations

from fastapi import status

from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.scans.application.use_cases.get_public_report import GetPublicReport
from src.scans.presentation.presenters.report import PublicReportPresenter


async def get_public_report(
    token: str,
    domain_context: DomainContextDep,
) -> ApiJSONResponse:
    view = await GetPublicReport(
        token=token,
        public_report_repository=domain_context.public_report_repository,
        scan_repository=domain_context.scan_repository,
    ).execute()

    findings = await domain_context.finding_repository.list_for_scan(view.scan.uuid)

    return ApiJSONResponse(
        content=PublicReportPresenter(scan=view.scan, findings=findings).to_dict,
        status_code=status.HTTP_200_OK,
    )
