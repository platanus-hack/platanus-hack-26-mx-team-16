"""SQL implementation of ``SiteRepository`` (06-data-model §3.1)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.sites.site import SiteORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.sites.domain.models.site import Site
from src.sites.domain.repositories.site import SiteRepository
from src.sites.domain.services.host import resolve_host_flags
from src.sites.infrastructure.builders.site import build_site


@dataclass
class SQLSiteRepository(SiteRepository):
    session: AsyncSession

    async def find(self, site_id: UUID) -> Site | None:
        result = await self.session.execute(
            select(SiteORM).where(SiteORM.uuid == site_id)
        )
        orm = result.scalar_one_or_none()
        return build_site(orm) if orm else None

    async def find_by_hostname(self, hostname: str) -> Site | None:
        orm = await self._find_orm_by_hostname(hostname)
        return build_site(orm) if orm else None

    async def get_or_create(
        self, url: str, *, owner_user_id: UUID | None = None, country: str | None = None
    ) -> Site:
        flags = resolve_host_flags(url)
        async with atomic_transaction(self.session):
            orm = await self._find_orm_by_hostname(flags.hostname)
            if orm is None:
                orm = SiteORM(
                    uuid=uuid.uuid4(),
                    url=url,
                    hostname=flags.hostname,
                    is_gov=flags.is_gov,  # server-derived, never from client
                    country=country,
                    owner_user_id=owner_user_id,
                )
                self.session.add(orm)
                await self.session.flush()
            return build_site(orm)

    async def set_latest_scan(self, site_id: UUID, scan_id: UUID) -> None:
        async with atomic_transaction(self.session):
            await self.session.execute(
                update(SiteORM)
                .where(SiteORM.uuid == site_id)
                .values(latest_scan_id=scan_id)
            )
            await self.session.flush()

    async def list_gov(self) -> list[Site]:
        result = await self.session.execute(
            select(SiteORM).where(SiteORM.is_gov.is_(True))
        )
        return [build_site(orm) for orm in result.scalars().all()]

    async def _find_orm_by_hostname(self, hostname: str) -> SiteORM | None:
        result = await self.session.execute(
            select(SiteORM).where(SiteORM.hostname == hostname)
        )
        return result.scalar_one_or_none()
