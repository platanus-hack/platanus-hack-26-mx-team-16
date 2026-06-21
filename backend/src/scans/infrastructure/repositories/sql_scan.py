"""SQL implementation of ``ScanRepository`` (06-data-model §3.2, §4)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.application.helpers.pagination import decode_cursor
from src.common.database.models.scans.scan import ScanORM
from src.common.database.models.sites.site import SiteORM
from src.common.domain.enums.scans import ScanStatus, ScanVisibility
from src.common.infrastructure.helpers.database import atomic_transaction
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
    ) -> tuple[Scan, bool]:
        # First chance: return the live scan if one already exists (created=False).
        existing = await self._find_active_orm(site_id, level)
        if existing is not None:
            return build_scan(existing), False

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
                # insert won; return the live scan instead of raising, with
                # created=False so the caller does NOT dispatch a second
                # RunScanCommand for the same row (§4 idempotency). Roll back the
                # poisoned transaction first, then re-query the existing scan.
                await self.session.rollback()
                existing = await self._find_active_orm(site_id, level)
                if existing is not None:
                    return build_scan(existing), False
                raise
        # The fresh INSERT succeeded — this call owns the row (created=True).
        return build_scan(orm), True

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
        # The UPDATE path triggers ``onupdate=func.now()`` for ``updated_at``
        # (server-side); SQLAlchemy expires that attribute after the flush since
        # it can't know the server-computed value (eager RETURNING is only used
        # for INSERT defaults, not UPDATE onupdate). Reading it later in
        # ``build_scan`` -> ``Scan.model_validate`` would lazily reload it,
        # triggering async IO outside a greenlet (MissingGreenlet). Re-fetch the
        # row inside the greenlet so the timestamps are populated before we read
        # them — same pattern as ``SQLWatchlistRepository.add``.
        await self.session.refresh(orm)
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
        # Worst-first over gov sites (the "Hall of Shame"): grade DESC so the
        # worst letter leads (F before B), penalty_raw DESC as tiebreak within a
        # grade (§4). The 07 spec prose's "ASC" notation was a slip — product
        # intent + tests are worst-first; LEADERBOARD_ORDER mirrors this DESC tuple.
        stmt = (
            select(ScanORM)
            .join(SiteORM, SiteORM.uuid == ScanORM.site_id)
            .where(SiteORM.is_gov.is_(True))
            .where(SiteORM.latest_scan_id == ScanORM.uuid)
            # Public ranking only: a gov site whose latest scan is private never
            # appears on the leaderboard (§3.1).
            .where(ScanORM.visibility == str(ScanVisibility.PUBLIC))
            .order_by(ScanORM.overall_grade.desc(), ScanORM.penalty_raw.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [build_scan(orm) for orm in result.scalars().all()]

    async def find_for_user(
        self,
        user_id: UUID,
        *,
        status: str | None = None,
        site_id: UUID | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> list[Scan]:
        stmt = (
            select(ScanORM)
            .where(ScanORM.requested_by == user_id)
            .order_by(ScanORM.created_at.desc(), ScanORM.uuid.desc())
            .limit(limit + 1)
        )
        if status is not None:
            stmt = stmt.where(ScanORM.status == status)
        if site_id is not None:
            stmt = stmt.where(ScanORM.site_id == site_id)
        if cursor is not None:
            created_at, last_uuid = decode_cursor(cursor)
            # Keyset on (created_at, uuid) descending — strictly "older than" the
            # cursor row so pages never overlap or skip.
            stmt = stmt.where(
                or_(
                    ScanORM.created_at < created_at,
                    and_(
                        ScanORM.created_at == created_at,
                        ScanORM.uuid < last_uuid,
                    ),
                )
            )
        result = await self.session.execute(stmt)
        return [build_scan(orm) for orm in result.scalars().all()]

    async def previous_graded_scan(
        self, site_id: UUID, *, before: UUID
    ) -> Scan | None:
        # The "before" anchor: we want the most recent terminal+graded scan of
        # the same site ordered strictly before the anchor scan. We keyset on
        # ``(created_at, uuid)`` — NOT ``created_at`` alone — because scans seeded
        # in the same DB transaction share an identical ``created_at`` (Postgres
        # ``now()`` is the transaction start time). A plain ``created_at <`` would
        # then drop a same-instant earlier scan; the uuid tie-break keeps the
        # ordering total and deterministic.
        anchor = await self.session.execute(
            select(ScanORM.created_at, ScanORM.uuid).where(ScanORM.uuid == before)
        )
        anchor_row = anchor.one_or_none()
        if anchor_row is None:
            return None
        anchor_created, anchor_uuid = anchor_row
        terminal = (str(ScanStatus.DONE), str(ScanStatus.PARTIAL))
        stmt = (
            select(ScanORM)
            .where(ScanORM.site_id == site_id)
            .where(ScanORM.uuid != before)
            .where(ScanORM.status.in_(terminal))
            .where(ScanORM.overall_grade.isnot(None))
            .where(
                or_(
                    ScanORM.created_at < anchor_created,
                    and_(
                        ScanORM.created_at == anchor_created,
                        ScanORM.uuid < anchor_uuid,
                    ),
                )
            )
            .order_by(ScanORM.created_at.desc(), ScanORM.uuid.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return build_scan(orm) if orm else None

    async def _find_active_orm(self, site_id: UUID, level: str) -> ScanORM | None:
        result = await self.session.execute(
            select(ScanORM).where(
                ScanORM.site_id == site_id,
                ScanORM.level == level,
                ScanORM.status.in_(_ACTIVE_STATUSES),
            )
        )
        return result.scalar_one_or_none()
