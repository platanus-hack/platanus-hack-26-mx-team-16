"""SQL implementation of ``AgenticSurfaceRepository`` (06-data-model §3.4)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.scans.agentic_surface import AgenticSurfaceORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.scans.domain.models.agentic_surface import AgenticSurface
from src.scans.domain.repositories.agentic_surface import AgenticSurfaceRepository
from src.scans.infrastructure.builders.scan import build_agentic_surface


@dataclass
class SQLAgenticSurfaceRepository(AgenticSurfaceRepository):
    session: AsyncSession

    async def add(self, surface: AgenticSurface) -> AgenticSurface:
        orm = AgenticSurfaceORM(
            uuid=surface.uuid or uuid.uuid4(),
            scan_id=surface.scan_id,
            site_id=surface.site_id,
            type=surface.type,
            vendor=surface.vendor,
            location_url=surface.location_url,
            inferred_model=surface.inferred_model,
        )
        async with atomic_transaction(self.session):
            self.session.add(orm)
            await self.session.flush()
        return build_agentic_surface(orm)

    async def list_for_scan(self, scan_id: UUID) -> list[AgenticSurface]:
        result = await self.session.execute(
            select(AgenticSurfaceORM).where(AgenticSurfaceORM.scan_id == scan_id)
        )
        return [build_agentic_surface(orm) for orm in result.scalars().all()]
