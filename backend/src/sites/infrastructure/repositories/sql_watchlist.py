"""SQL implementation of ``WatchlistRepository`` (06-data-model §3.6)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.sites.watchlist import WatchlistORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.sites.domain.models.watchlist import WatchlistEntry
from src.sites.domain.repositories.watchlist import WatchlistRepository
from src.sites.infrastructure.builders.site import build_watchlist_entry


@dataclass
class SQLWatchlistRepository(WatchlistRepository):
    session: AsyncSession

    async def add(
        self, user_id: UUID, site_id: UUID, *, monitor: bool = True
    ) -> WatchlistEntry:
        existing = await self._find_orm(user_id, site_id)
        if existing is not None:
            async with atomic_transaction(self.session):
                existing.monitor = monitor
                await self.session.flush()
            # ``atomic_transaction`` commits on exit, which (with the default
            # ``expire_on_commit=True``) expires every ORM attribute. Building the
            # domain entity then lazily reloads ``created_at``/``updated_at``,
            # triggering async IO outside a greenlet context (MissingGreenlet ->
            # 500). Re-fetch the row inside the greenlet so the timestamps are
            # populated before we read them.
            await self.session.refresh(existing)
            return build_watchlist_entry(existing)
        orm = WatchlistORM(
            uuid=uuid.uuid4(), user_id=user_id, site_id=site_id, monitor=monitor
        )
        async with atomic_transaction(self.session):
            self.session.add(orm)
            await self.session.flush()
        await self.session.refresh(orm)
        return build_watchlist_entry(orm)

    async def remove(self, user_id: UUID, site_id: UUID) -> None:
        async with atomic_transaction(self.session):
            await self.session.execute(
                delete(WatchlistORM).where(
                    WatchlistORM.user_id == user_id, WatchlistORM.site_id == site_id
                )
            )

    async def list_for_user(self, user_id: UUID) -> list[WatchlistEntry]:
        result = await self.session.execute(
            select(WatchlistORM).where(WatchlistORM.user_id == user_id)
        )
        return [build_watchlist_entry(orm) for orm in result.scalars().all()]

    async def find(self, user_id: UUID, site_id: UUID) -> WatchlistEntry | None:
        orm = await self._find_orm(user_id, site_id)
        return build_watchlist_entry(orm) if orm else None

    async def sites_with_monitor_true(self) -> list[WatchlistEntry]:
        result = await self.session.execute(
            select(WatchlistORM).where(WatchlistORM.monitor.is_(True))
        )
        return [build_watchlist_entry(orm) for orm in result.scalars().all()]

    async def _find_orm(self, user_id: UUID, site_id: UUID) -> WatchlistORM | None:
        result = await self.session.execute(
            select(WatchlistORM).where(
                WatchlistORM.user_id == user_id, WatchlistORM.site_id == site_id
            )
        )
        return result.scalar_one_or_none()
