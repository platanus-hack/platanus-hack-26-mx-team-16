from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.common.application.helpers.pagination import decode_cursor, encode_cursor
from src.common.database.models import UserORM
from src.common.database.models.email_address import EmailAddressORM
from src.common.database.models.tenants.tenant_user import TenantUserORM
from src.common.domain.entities.common.pagination import Page
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.enums.users import TenantUserStatus
from src.common.domain.exceptions.users import TenantUserNotFoundError
from src.common.domain.filters.tenants.tenant_user import TenantUserFilters
from src.common.domain.helpers.models import override_dict_properties
from src.common.infrastructure.builders.tenants.tenant_user import build_tenant_user
from src.common.infrastructure.helpers.database import atomic_transaction
from src.tenants.domain.repositories.tenant_user import TenantUserRepository


@dataclass
class SQLTenantUserRepository(TenantUserRepository):
    session: AsyncSession

    @classmethod
    def _build_base_query(cls) -> select:
        return select(TenantUserORM).options(
            selectinload(TenantUserORM.user).selectinload(UserORM.email_address),
            selectinload(TenantUserORM.user).selectinload(UserORM.phone_number),
            selectinload(TenantUserORM.tenant_role),
            selectinload(TenantUserORM.tenant),
        )

    async def find(self, instance_id: UUID) -> TenantUser | None:
        orm_instance = await self._find(instance_id)
        if not orm_instance:
            return None
        return build_tenant_user(orm_instance)

    async def find_by_args(
        self,
        user_id: UUID,
        tenant_id: UUID,
        status: TenantUserStatus | None = None,
    ) -> TenantUser | None:
        stmt = self._build_base_query().where(
            TenantUserORM.tenant_id == tenant_id,
            TenantUserORM.user_id == user_id,
        )

        if status:
            stmt = stmt.where(TenantUserORM.status == str(status))

        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()
        if not orm_instance:
            return None
        return build_tenant_user(orm_instance)

    async def persist(
        self,
        instance: TenantUser,
    ) -> TenantUser:
        async with atomic_transaction(self.session):
            orm_instance = await self._find(instance.uuid)
            persist_data = instance.to_persist_dict

            if orm_instance:
                override_dict_properties(orm_instance, persist_data)
            else:
                orm_instance = TenantUserORM(**persist_data)
                self.session.add(orm_instance)

            await self.session.flush()
            orm_instance = await self._find(orm_instance.uuid)

        if not orm_instance:
            raise TenantUserNotFoundError

        return build_tenant_user(orm_instance)

    async def filter(
        self,
        filters: TenantUserFilters,
    ) -> list[TenantUser]:
        stmt = await self._filter(filters, paginated=False)

        result = await self.session.execute(stmt)
        orm_instances = list(result.scalars())

        return [build_tenant_user(orm_instance) for orm_instance in orm_instances]

    async def filter_paginated(
        self,
        filters: TenantUserFilters,
    ) -> Page[TenantUser]:
        stmt = await self._filter(filters, paginated=True)

        result = await self.session.execute(stmt)
        orm_instances = list(result.scalars())

        next_cursor = None
        if len(orm_instances) == filters.limit + 1:
            last = orm_instances.pop()
            next_cursor = encode_cursor(last.created_at, last.uuid)

        return Page(
            next_cursor=next_cursor,
            items=[build_tenant_user(orm_instance) for orm_instance in orm_instances],
            limit=filters.limit,
        )

    async def remove(
        self,
        tenant_user_id: UUID,
    ) -> None:
        async with atomic_transaction(self.session):
            tenant_user_orm = await self._find(tenant_user_id)
            if tenant_user_orm is None:
                return

            await self.session.delete(tenant_user_orm)
            await self.session.flush()

    async def count_by_status(
        self,
        tenant_id: UUID,
        excluded_tenant_user_ids: list[UUID] | None = None,
    ) -> dict[TenantUserStatus, int]:
        stmt = (
            select(
                TenantUserORM.status,
                func.count(),
            )
            .where(
                TenantUserORM.tenant_id == tenant_id,
                or_(TenantUserORM.is_support == False, TenantUserORM.is_support.is_(None)),
            )
            .group_by(TenantUserORM.status)
        )

        if excluded_tenant_user_ids:
            stmt = stmt.where(TenantUserORM.uuid.notin_(excluded_tenant_user_ids))

        result = await self.session.execute(stmt)

        raw_counts: dict[TenantUserStatus, int] = {}
        for status_str, count in result.all():
            status_enum = TenantUserStatus.from_value(status_str)
            if status_enum:
                raw_counts[status_enum] = count

        return {status: raw_counts.get(status, 0) for status in TenantUserStatus}

    async def remove_tenant_users(
        self,
        tenant_id: UUID,
    ) -> None:
        async with atomic_transaction(self.session):
            stmt = select(TenantUserORM).where(TenantUserORM.tenant_id == tenant_id)
            result = await self.session.execute(stmt)
            tenant_users = list(result.scalars())

            for tenant_user in tenant_users:
                await self.session.delete(tenant_user)

            await self.session.flush()

    async def _find(self, instance_id: UUID) -> TenantUserORM | None:
        stmt = self._build_base_query().where(TenantUserORM.uuid == instance_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _filter(self, filters: TenantUserFilters, paginated: bool = False) -> Select:
        base_query = (
            self._build_base_query()
            .where(or_(TenantUserORM.is_support == False, TenantUserORM.is_support.is_(None)))
            .order_by(TenantUserORM.created_at.desc(), TenantUserORM.uuid.desc())
        )

        if paginated:
            base_query = base_query.limit(filters.limit + 1)

        if filters.tenant_ids:
            base_query = base_query.where(TenantUserORM.tenant_id.in_(filters.tenant_ids))

        if filters.exclude_ids:
            base_query = base_query.where(TenantUserORM.uuid.notin_(filters.exclude_ids))

        if filters.enum_statuses:
            base_query = base_query.where(TenantUserORM.status.in_(filters.enum_statuses))

        if filters.search:
            search_pattern = f"%{filters.search}%"
            base_query = base_query.join(TenantUserORM.user).join(
                EmailAddressORM,
                UserORM.email_address_id == EmailAddressORM.uuid,
                isouter=True,
            )
            base_query = base_query.where(
                or_(
                    TenantUserORM.first_name.ilike(search_pattern),
                    TenantUserORM.last_name.ilike(search_pattern),
                    UserORM.first_name.ilike(search_pattern),
                    UserORM.last_name.ilike(search_pattern),
                    EmailAddressORM.email.ilike(search_pattern),
                )
            )

        if filters.cursor:
            timestamp, last_uuid = decode_cursor(filters.cursor)
            base_query = base_query.where(
                tuple_(TenantUserORM.created_at, TenantUserORM.uuid) <= (timestamp, last_uuid)
            )

        return base_query
