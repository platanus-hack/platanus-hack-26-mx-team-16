"""SQL implementation of ``ScanRepository`` (06-data-model §3.2, §4)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.scans.scan import ScanORM
from src.common.database.models.sites.site import SiteORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.common.domain.enums.scans import ScanStatus
from src.scans.domain.models.scan import Scan
from src.scans.domain.repositories.scan import ScanRepository
from src.scans.infrastructure.builders.scan import build_scan

_ACTIVE_STATUSES = (str(ScanStatus.QUEUED), str(ScanStatus.RUNNING))


@dataclass
class SQLScanRepository(ScanRepository):
    session: AsyncSession

    async def find(self, scan_id: UUID) -> Scan | None:
        result = await self.session.execute(
            select(ScanORM).where(ScanORM.uuid == scan_id)
        )
        orm = result.scalar_one_or_none()
        return build_scan(orm) if orm else None

    async def find_active(self, site_id: UUID, level: str) -> Scan | None:
        orm = await self._find_active_orm(site_id, level)
        return build_scan(orm) if orm else None

    async def enqueue(
        self,
        site_id: UUID,
        level: str,
        *,
        visibility: str,
        requested_by: UUID | None = None,
        authorized: bool = False,
    ) -> Scan:
        # First chance: return the live scan if one already exists.
        existing = await self._find_active_orm(site_id, level)
        if existing is not None:
            return build_scan(existing)

        orm = ScanORM(
            uuid=uuid.uuid4(),
            site_id=site_id,
            level=level,
            status=str(ScanStatus.QUEUED),
            visibility=visibility,
            requested_by=requested_by,
            authorized=authorized,
        )
        async with atomic_transaction(self.session):
            self.session.add(orm)
            try:
                await self.session.flush()
            except IntegrityError:
                # Lost the race against the partial unique index — the other
                # insert won; return the live scan instead of raising
                # (§4 idempotency). Roll back the poisoned transaction first,
                # then re-query the existing live scan.
                await self.session.rollback()
                existing = await self._find_active_orm(site_id, level)
                if existing is not None:
                    return build_scan(existing)
                raise
        return build_scan(orm)

    async def persist(self, scan: Scan) -> Scan:
        data = scan.model_dump(exclude={"created_at", "updated_at"})
        scan_id = data.pop("uuid")
        async with atomic_transaction(self.session):
            result = await self.session.execute(
                select(ScanORM).where(ScanORM.uuid == scan_id)
            )
            orm = result.scalar_one_or_none()
            if orm is None:
                orm = ScanORM(uuid=scan_id, **data)
                self.session.add(orm)
            else:
                for key, value in data.items():
                    setattr(orm, key, value)
            await self.session.flush()
        return build_scan(orm)

    async def update_progress(
        self,
        scan_id: UUID,
        *,
        progress: int | None = None,
        current_phase: str | None = None,
        tools_status: dict | None = None,
        coverage: list | None = None,
        status: str | None = None,
        error: str | None = None,
    ) -> None:
        values: dict = {}
        if progress is not None:
            values["progress"] = progress
        if current_phase is not None:
            values["current_phase"] = current_phase
        if tools_status is not None:
            values["tools_status"] = tools_status
        if coverage is not None:
            values["coverage"] = coverage
        if status is not None:
            values["status"] = status
        if error is not None:
            values["error"] = error
        if not values:
            return
        async with atomic_transaction(self.session):
            await self.session.execute(
                update(ScanORM).where(ScanORM.uuid == scan_id).values(**values)
            )

    async def leaderboard(
        self, *, limit: int = 50, cursor: str | None = None
    ) -> list[Scan]:
        # Worst-first over gov sites: grade ASC, penalty_raw DESC (§4).
        stmt = (
            select(ScanORM)
            .join(SiteORM, SiteORM.uuid == ScanORM.site_id)
            .where(SiteORM.is_gov.is_(True))
            .where(SiteORM.latest_scan_id == ScanORM.uuid)
            .order_by(ScanORM.overall_grade.asc(), ScanORM.penalty_raw.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [build_scan(orm) for orm in result.scalars().all()]

    async def _find_active_orm(self, site_id: UUID, level: str) -> ScanORM | None:
        result = await self.session.execute(
            select(ScanORM).where(
                ScanORM.site_id == site_id,
                ScanORM.level == level,
                ScanORM.status.in_(_ACTIVE_STATUSES),
            )
        )
        return result.scalar_one_or_none()
