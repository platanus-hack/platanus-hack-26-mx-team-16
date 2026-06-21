"""``CreatePublicShare`` — ``POST /scans/{id}/share`` (12-api §"Reporte público").

Mints a public, redacted-report link for an owned scan. The opaque token
(``secrets.token_urlsafe(32)``, UNIQUE) and the row are created by the repo (06);
this use case only computes the expiry from ``ttl_days`` (default 7) and delegates.
Ownership (404 for non-owner) is enforced by ``require_scan_owner`` upstream.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.common.domain.interfaces.use_case import UseCase
from src.scans.domain.models.public_report import PublicReport
from src.scans.domain.models.scan import Scan
from src.scans.domain.repositories.public_report import PublicReportRepository

DEFAULT_TTL_DAYS = 7


@dataclass
class CreatePublicShare(UseCase):
    scan: Scan
    public_report_repository: PublicReportRepository
    ttl_days: int | None = None

    async def execute(self, *args, **kwargs) -> PublicReport:
        ttl_days = self.ttl_days if self.ttl_days is not None else DEFAULT_TTL_DAYS
        expires_at = datetime.now(UTC) + timedelta(days=ttl_days)
        return await self.public_report_repository.create(
            self.scan.uuid, expires_at=expires_at
        )
