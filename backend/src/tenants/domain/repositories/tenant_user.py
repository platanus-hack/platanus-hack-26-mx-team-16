from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.entities.common.pagination import Page
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.enums.users import TenantUserStatus
from src.common.domain.filters.tenants.tenant_user import TenantUserFilters


class TenantUserRepository(ABC):
    @abstractmethod
    async def find(self, instance_id: UUID) -> TenantUser | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_args(
        self,
        user_id: UUID,
        tenant_id: UUID,
        status: TenantUserStatus | None = None,
    ) -> TenantUser | None:
        raise NotImplementedError

    @abstractmethod
    async def persist(
        self,
        instance: TenantUser,
    ) -> TenantUser:
        raise NotImplementedError

    @abstractmethod
    async def filter(
        self,
        filters: TenantUserFilters,
    ) -> list[TenantUser]:
        raise NotImplementedError

    @abstractmethod
    async def filter_paginated(
        self,
        filters: TenantUserFilters,
    ) -> Page[TenantUser]:
        raise NotImplementedError

    @abstractmethod
    async def remove(
        self,
        tenant_user_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def count_by_status(
        self,
        tenant_id: UUID,
        excluded_tenant_user_ids: list[UUID] | None = None,
    ) -> dict[TenantUserStatus, int]:
        raise NotImplementedError

    @abstractmethod
    async def remove_tenant_users(
        self,
        tenant_id: UUID,
    ) -> None:
        raise NotImplementedError
