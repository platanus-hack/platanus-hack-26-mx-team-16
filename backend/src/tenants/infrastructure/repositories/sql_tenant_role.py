from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.application.helpers.pagination import decode_cursor, encode_cursor
from src.common.database.models.tenants.tenant_role import TenantRoleORM
from src.common.domain.entities.common.collection import ListFilters
from src.common.domain.entities.common.pagination import Page
from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.enums.tenants import TenantRoleStatus
from src.common.domain.helpers.models import override_dict_properties
from src.common.infrastructure.builders.tenants.tenant_role import build_tenant_role
from src.common.infrastructure.helpers.database import atomic_transaction
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository


@dataclass
class SQLTenantRoleRepository(TenantRoleRepository):
    session: AsyncSession

    async def find(
        self,
        instance_id: UUID,
    ) -> TenantRole | None:
        stmt = select(TenantRoleORM).where(
            TenantRoleORM.uuid == instance_id,
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()

        return build_tenant_role(orm_instance) if orm_instance else None

    async def filter(
        self,
        tenant_id: UUID | None,
        filters: ListFilters,
    ) -> list[TenantRole]:
        stmt = self._build_filter_query(
            tenant_id=tenant_id,
            filters=filters,
        ).limit(filters.limit)

        result = await self.session.execute(stmt)
        orm_instances = list(result.scalars())

        return [build_tenant_role(orm_instance) for orm_instance in orm_instances]

    async def filter_paginated(
        self,
        tenant_id: UUID | None,
        filters: ListFilters,
    ) -> Page[TenantRole]:
        base_query = self._build_filter_query(
            tenant_id=tenant_id,
            filters=filters,
        ).limit(filters.limit + 1)

        result = await self.session.execute(base_query)
        orm_instances = list(result.scalars())

        next_cursor = None
        if len(orm_instances) == filters.limit + 1:
            last = orm_instances.pop()
            next_cursor = encode_cursor(last.created_at, last.uuid)

        return Page(
            next_cursor=next_cursor,
            items=[build_tenant_role(orm_instance) for orm_instance in orm_instances],
            limit=filters.limit,
        )

    async def persist(
        self,
        instance: TenantRole,
    ) -> TenantRole:
        async with atomic_transaction(self.session):
            orm_instance = await self.session.get(TenantRoleORM, instance.uuid)

            if orm_instance:
                override_dict_properties(orm_instance, instance.to_persist_dict)
            else:
                orm_instance = TenantRoleORM(
                    uuid=instance.uuid,
                    **instance.to_persist_dict,
                )
                self.session.add(orm_instance)
            await self.session.flush()
            await self.session.refresh(orm_instance)

        return build_tenant_role(orm_instance)

    async def delete(
        self,
        instance_id: UUID,
    ) -> None:
        async with atomic_transaction(self.session):
            orm_instance = await self.session.get(TenantRoleORM, instance_id)
            if orm_instance:
                await self.session.delete(orm_instance)
                await self.session.flush()

    async def remove_by_tenant_id(
        self,
        tenant_id: UUID,
    ) -> None:
        async with atomic_transaction(self.session):
            stmt = select(TenantRoleORM).where(TenantRoleORM.tenant_id == tenant_id)
            result = await self.session.execute(stmt)
            tenant_roles = list(result.scalars())

            for role in tenant_roles:
                await self.session.delete(role)

            await self.session.flush()

    # Additional helper methods
    async def find_by_name(
        self,
        instance_id: UUID,
        name: str,
    ) -> TenantRole | None:
        stmt = select(TenantRoleORM).where(
            TenantRoleORM.tenant_id == instance_id,
            TenantRoleORM.name == name,
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()

        return build_tenant_role(orm_instance) if orm_instance else None

    async def find_by_slug(
        self,
        tenant_id: UUID,
        slug: str,
    ) -> TenantRole | None:
        stmt = select(TenantRoleORM).where(
            TenantRoleORM.tenant_id == tenant_id,
            TenantRoleORM.slug == slug,
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()

        return build_tenant_role(orm_instance) if orm_instance else None

    async def find_active_roles(
        self,
        tenant_id: UUID,
    ) -> list[TenantRole]:
        """Find all active roles for a tenant"""
        stmt = (
            select(TenantRoleORM)
            .where(
                TenantRoleORM.tenant_id == tenant_id,
                TenantRoleORM.status == TenantRoleStatus.ACTIVE,
            )
            .order_by(TenantRoleORM.name)
        )
        result = await self.session.execute(stmt)
        orm_instances = result.scalars().all()

        return [build_tenant_role(orm_instance) for orm_instance in orm_instances]

    def _build_filter_query(
        self,
        tenant_id: UUID | None,
        filters: ListFilters,
    ) -> Select:
        stmt = select(TenantRoleORM).order_by(
            TenantRoleORM.created_at.desc(),
            TenantRoleORM.uuid.desc(),
        )

        if tenant_id:
            stmt = stmt.where(TenantRoleORM.tenant_id == tenant_id)

        if filters.cursor:
            timestamp, last_uuid = decode_cursor(filters.cursor)
            stmt = stmt.where(tuple_(TenantRoleORM.created_at, TenantRoleORM.uuid) <= (timestamp, last_uuid))

        return stmt
