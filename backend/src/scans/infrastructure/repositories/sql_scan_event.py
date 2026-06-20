"""SQL implementation of ``ScanEventRepository`` — append by monotonic seq
(06-data-model §3.5, §4)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.scans.scan_event import ScanEventORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.scans.domain.contracts.events import ScanEvent
from src.scans.domain.repositories.scan_event import ScanEventRepository
from src.scans.infrastructure.builders.scan import build_scan_event


@dataclass
class SQLScanEventRepository(ScanEventRepository):
    session: AsyncSession

    async def append(self, event: ScanEvent) -> ScanEvent:
        orm = ScanEventORM(
            uuid=uuid.uuid4(),
            scan_id=event.scan_id,
            seq=event.seq,
            ts=event.ts,
            type=event.type,
            agent=event.agent,
            tool=event.tool,
            severity=event.severity,
            message=event.message,
            payload=event.payload,
            progress=event.progress,
        )
        async with atomic_transaction(self.session):
            self.session.add(orm)
            # raises IntegrityError on duplicate (scan_id, seq); the wrapper
            # rolls back and re-raises.
            await self.session.flush()
        return build_scan_event(orm)

    async def next_seq(self, scan_id: UUID) -> int:
        result = await self.session.execute(
            select(func.max(ScanEventORM.seq)).where(ScanEventORM.scan_id == scan_id)
        )
        current = result.scalar_one_or_none()
        return 0 if current is None else current + 1

    async def replay(
        self, scan_id: UUID, *, after_seq: int | None = None
    ) -> list[ScanEvent]:
        stmt = select(ScanEventORM).where(ScanEventORM.scan_id == scan_id)
        if after_seq is not None:
            stmt = stmt.where(ScanEventORM.seq > after_seq)
        stmt = stmt.order_by(ScanEventORM.seq.asc())
        result = await self.session.execute(stmt)
        return [build_scan_event(orm) for orm in result.scalars().all()]
