"""``GetPublicReport`` — ``GET /r/{token}`` (12-api §"Reporte público").

Token contract:
- token unknown            → ``PublicReportNotFoundError`` (404)
- expired or revoked       → ``PublicReportGoneError`` (410, "Este enlace expiró")
- valid                    → the report's scan (redaction + render owned by 09)

This use case resolves the token to its ``Scan`` and enforces the 404/410 split
via ``PublicReport.is_servable``. The redacted projection (exec layer + technical
findings WITHOUT exploit payloads) is applied by the presenter / 09-reporting.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.common.domain.interfaces.use_case import UseCase
from src.scans.domain.models.scan import Scan
from src.scans.domain.repositories.public_report import PublicReportRepository
from src.scans.domain.repositories.scan import ScanRepository
from src.scans.presentation.exceptions import (
    PublicReportGoneError,
    PublicReportNotFoundError,
)


@dataclass
class PublicReportView:
    scan: Scan


@dataclass
class GetPublicReport(UseCase):
    token: str
    public_report_repository: PublicReportRepository
    scan_repository: ScanRepository

    async def execute(self, *args, **kwargs) -> PublicReportView:
        report = await self.public_report_repository.find_by_token(self.token)
        if report is None:
            raise PublicReportNotFoundError
        if not report.is_servable():
            raise PublicReportGoneError(context={"token": self.token})

        scan = await self.scan_repository.find(report.scan_id)
        if scan is None:
            # The report points at a scan that no longer exists — treat as gone.
            raise PublicReportGoneError(context={"token": self.token})
        return PublicReportView(scan=scan)
