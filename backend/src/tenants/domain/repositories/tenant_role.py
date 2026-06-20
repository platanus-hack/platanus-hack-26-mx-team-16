from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.entities.common.collection import ListFilters
from src.common.domain.entities.common.pagination import Page
from src.common.domain.models.tenants.tenant_role import TenantRole


class TenantRoleRepository(ABC):
    @abstractmethod
    async def find(
        self,
        instance_id: UUID,
    ) -> TenantRole | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_name(
        self,
        instance_id: UUID,
        name: str,
    ) -> TenantRole | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_slug(
        self,
        tenant_id: UUID,
        slug: str,
    ) -> TenantRole | None:
        raise NotImplementedError

    @abstractmethod
    async def filter(
        self,
        tenant_id: UUID | None,
        filters: ListFilters,
    ) -> list[TenantRole]:
        raise NotImplementedError

    @abstractmethod
    async def filter_paginated(
        self,
        tenant_id: UUID | None,
        filters: ListFilters,
    ) -> Page[TenantRole]:
        raise NotImplementedError

    @abstractmethod
    async def persist(
        self,
        instance: TenantRole,
    ) -> TenantRole:
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        instance_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def remove_by_tenant_id(
        self,
        tenant_id: UUID,
    ) -> None:
        raise NotImplementedError
