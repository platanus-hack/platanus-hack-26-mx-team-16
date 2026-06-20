"""SQL implementation of ``PublicReportRepository`` (06-data-model §3.7, §4)."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.scans.public_report import PublicReportORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.scans.domain.models.public_report import PublicReport
from src.scans.domain.repositories.public_report import PublicReportRepository
from src.scans.infrastructure.builders.scan import build_public_report


@dataclass
class SQLPublicReportRepository(PublicReportRepository):
    session: AsyncSession

    async def create(
        self, scan_id: UUID, *, expires_at: datetime | None = None
    ) -> PublicReport:
        orm = PublicReportORM(
            uuid=uuid.uuid4(),
            token=secrets.token_urlsafe(32),
            scan_id=scan_id,
            expires_at=expires_at,
        )
        async with atomic_transaction(self.session):
            self.session.add(orm)
            await self.session.flush()
        return build_public_report(orm)

    async def find_by_token(self, token: str) -> PublicReport | None:
        result = await self.session.execute(
            select(PublicReportORM).where(PublicReportORM.token == token)
        )
        orm = result.scalar_one_or_none()
        return build_public_report(orm) if orm else None

    async def revoke(self, token: str) -> None:
        async with atomic_transaction(self.session):
            await self.session.execute(
                update(PublicReportORM)
                .where(PublicReportORM.token == token)
                .values(revoked_at=datetime.now(timezone.utc))
            )
