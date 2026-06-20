from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.common.application.logging import get_logger
from src.common.database.models import UserORM
from src.common.database.models.tenants.tenant import TenantORM
from src.common.database.models.tenants.tenant_user import TenantUserORM
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.enums.users import TenantUserStatus
from src.common.domain.helpers.models import override_dict_properties
from src.common.infrastructure.builders.tenants.tenant import build_tenant
from src.common.infrastructure.helpers.database import atomic_transaction
from src.tenants.domain.repositories.tenant import TenantRepository

logger = get_logger(__name__)


@dataclass
class SQLTenantRepository(TenantRepository):
    session: AsyncSession

    async def find(self, tenant_id: UUID, include_deleted: bool = False) -> Tenant | None:
        try:
            orm_instance = await self._find(tenant_id, include_deleted=include_deleted)
            if orm_instance is None:
                logger.debug("tenant.not_found", tenant_id=str(tenant_id))
                return None
            return build_tenant(orm_instance)
        except Exception as e:
            logger.error(
                "tenant.find.failed",
                tenant_id=str(tenant_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def find_by_user(
        self,
        user_id: UUID,
    ) -> Tenant | None:
        orm_user = await self._find_user(user_id)

        if orm_user.current_tenant_id:
            tenant = await self.find(tenant_id=orm_user.current_tenant_id)
            return tenant if tenant and tenant.is_active else None

        user_tenants = await self.filter_by_user(user_id)
        if not user_tenants:
            return None

        user_tenant = user_tenants[0]

        async with atomic_transaction(self.session):
            if user_tenant:
                orm_user.current_tenant_id = user_tenant.uuid
                self.session.add(orm_user)
                await self.session.flush()
        return user_tenant

    async def find_by_slug(self, tenant_slug: str) -> Tenant | None:
        stmt = select(TenantORM).where(
            TenantORM.slug == tenant_slug,
            TenantORM.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()
        return build_tenant(orm_instance) if orm_instance else None

    async def find_all_by_name(self, name: str) -> list[Tenant]:
        stmt = (
            select(TenantORM)
            .where(TenantORM.name == name, TenantORM.is_deleted.is_(False))
            .order_by(TenantORM.created_at.asc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [build_tenant(r) for r in rows]

    async def persist(self, instance: Tenant) -> Tenant:
        async with atomic_transaction(self.session):
            orm_instance = await self._find(tenant_id=instance.uuid)

            if orm_instance:
                override_dict_properties(orm_instance, instance.persist_dict)
            else:
                orm_instance = TenantORM(**instance.persist_dict)
                self.session.add(orm_instance)

            await self.session.flush()
            orm_instance = await self._find(orm_instance.uuid, include_deleted=True)
            return build_tenant(orm_instance)

    async def filter_by_user(self, user_id: UUID) -> list[Tenant]:
        query = (
            select(TenantORM)
            .join(TenantUserORM, TenantUserORM.tenant_id == TenantORM.uuid)
            .where(
                TenantUserORM.user_id == user_id,
                TenantUserORM.status == str(TenantUserStatus.ACTIVE),
                TenantORM.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(query)
        return [build_tenant(orm) for orm in result.scalars().all()]

    async def get_slug_count(self, slug: str) -> int:
        stmt = select(func.count()).select_from(TenantORM).where(TenantORM.slug.startswith(slug))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def remove(self, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            orm_instance = await self._find(tenant_id, include_deleted=False)
            if orm_instance:
                await self.session.delete(orm_instance)

    async def _find(self, tenant_id: UUID, include_deleted: bool = False) -> TenantORM | None:
        conditions = [TenantORM.uuid == tenant_id]
        if not include_deleted:
            conditions.append(TenantORM.is_deleted.is_(False))
        stmt = select(TenantORM).where(*conditions)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_user(self, user_id: UUID) -> UserORM | None:
        stmt = (
            select(UserORM)
            .options(
                selectinload(UserORM.email_address),
                selectinload(UserORM.phone_number),
                selectinload(UserORM.current_tenant),
            )
            .where(UserORM.uuid == user_id)
        )
        result = await self.session.execute(stmt)
        orm_instance: UserORM | None = result.scalar_one_or_none()
        return orm_instance
