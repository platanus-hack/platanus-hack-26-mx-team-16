from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.models.tenants.tenant import Tenant


class TenantRepository(ABC):
    @abstractmethod
    async def find(self, tenant_id: UUID, include_deleted: bool = False) -> Tenant | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_user(
        self,
        user_id: UUID,
    ) -> Tenant | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_slug(self, tenant_slug: str) -> Tenant | None:
        raise NotImplementedError

    @abstractmethod
    async def find_all_by_name(self, name: str) -> list[Tenant]:
        """Exact-name lookup, soft-deleted excluded, oldest-first."""
        raise NotImplementedError

    @abstractmethod
    async def persist(self, instance: Tenant) -> Tenant | None:
        raise NotImplementedError

    @abstractmethod
    async def filter_by_user(self, user_id: UUID) -> list[Tenant]:
        raise NotImplementedError

    @abstractmethod
    async def get_slug_count(self, slug: str) -> int:
        raise NotImplementedError

    @abstractmethod
    async def remove(self, tenant_id: UUID) -> None:
        raise NotImplementedError
