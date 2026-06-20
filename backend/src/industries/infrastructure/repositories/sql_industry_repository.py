"""SQLAlchemy implementation of IndustryRepository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.processing.industry import IndustryORM
from src.common.database.models.tenant_industry import TenantIndustryORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.common.domain.models.industry import Industry
from src.common.domain.exceptions.industries import IndustryNotFoundError
from src.industries.domain.repositories.industry_repository import IndustryRepository
from src.industries.infrastructure.builders.industry_builder import build_industry


class SQLIndustryRepository(IndustryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_slug(self, slug: str) -> Industry | None:
        stmt = select(IndustryORM).where(IndustryORM.slug == slug)
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()
        if orm_instance is None:
            return None
        return build_industry(orm_instance)

    async def find_by_id(self, industry_id: UUID) -> Industry | None:
        stmt = select(IndustryORM).where(IndustryORM.uuid == industry_id)
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()
        if orm_instance is None:
            return None
        return build_industry(orm_instance)

    async def list_all(self) -> list[Industry]:
        stmt = select(IndustryORM).order_by(IndustryORM.name.asc())
        result = await self.session.execute(stmt)
        orm_instances = list(result.scalars())
        return [build_industry(orm) for orm in orm_instances]

    async def find_by_tenant_ids(
        self,
        tenant_ids: list[UUID],
    ) -> dict[UUID, list[Industry]]:
        if not tenant_ids:
            return {}

        stmt = (
            select(TenantIndustryORM.tenant_id, IndustryORM)
            .join(IndustryORM, TenantIndustryORM.industry_id == IndustryORM.uuid)
            .where(TenantIndustryORM.tenant_id.in_(tenant_ids))
            .order_by(IndustryORM.name.asc())
        )
        result = await self.session.execute(stmt)
        grouped: dict[UUID, list[Industry]] = {tid: [] for tid in tenant_ids}
        for tenant_id, orm_industry in result.all():
            grouped[tenant_id].append(build_industry(orm_industry))
        return grouped

    async def assign_to_tenant(
        self,
        tenant_id: UUID,
        industry_id: UUID,
    ) -> None:
        # Postgres ON CONFLICT DO NOTHING keeps the call idempotent and
        # avoids racing two concurrent assignments — the unique
        # constraint on (tenant_id, industry_id) is the source of truth.
        async with atomic_transaction(self.session):
            stmt = (
                pg_insert(TenantIndustryORM)
                .values(tenant_id=tenant_id, industry_id=industry_id)
                .on_conflict_do_nothing(
                    index_elements=["tenant_id", "industry_id"],
                )
            )
            await self.session.execute(stmt)

    async def create(self, industry: Industry) -> Industry:
        async with atomic_transaction(self.session):
            orm_instance = IndustryORM(
                uuid=industry.uuid,
                slug=industry.slug,
                name=industry.name,
                icon=industry.icon,
                description=industry.description,
            )
            self.session.add(orm_instance)
            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_industry(orm_instance)

    async def update(self, industry: Industry) -> Industry:
        async with atomic_transaction(self.session):
            stmt = select(IndustryORM).where(IndustryORM.uuid == industry.uuid)
            result = await self.session.execute(stmt)
            try:
                orm_instance = result.scalar_one()
            except NoResultFound:
                raise IndustryNotFoundError(str(industry.uuid))

            orm_instance.slug = industry.slug
            orm_instance.name = industry.name
            orm_instance.icon = industry.icon
            orm_instance.description = industry.description

            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_industry(orm_instance)

    async def delete(self, industry_id: UUID) -> None:
        async with atomic_transaction(self.session):
            stmt = select(IndustryORM).where(IndustryORM.uuid == industry_id)
            result = await self.session.execute(stmt)
            try:
                orm_instance = result.scalar_one()
            except NoResultFound:
                raise IndustryNotFoundError(str(industry_id))

            await self.session.delete(orm_instance)
            await self.session.flush()
