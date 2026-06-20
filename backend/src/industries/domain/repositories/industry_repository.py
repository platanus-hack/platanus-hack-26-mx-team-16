from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.models.industry import Industry


class IndustryRepository(ABC):
    @abstractmethod
    async def find_by_slug(self, slug: str) -> Industry | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, industry_id: UUID) -> Industry | None:
        raise NotImplementedError

    @abstractmethod
    async def list_all(self) -> list[Industry]:
        raise NotImplementedError

    @abstractmethod
    async def find_by_tenant_ids(
        self,
        tenant_ids: list[UUID],
    ) -> dict[UUID, list[Industry]]:
        """Industries grouped by tenant_id, joined via tenant_industries."""
        raise NotImplementedError

    @abstractmethod
    async def assign_to_tenant(
        self,
        tenant_id: UUID,
        industry_id: UUID,
    ) -> None:
        """Link an industry to a tenant via the `tenant_industries`
        pivot. Idempotent — a second call for the same pair is a no-op."""
        raise NotImplementedError

    @abstractmethod
    async def create(self, industry: Industry) -> Industry:
        raise NotImplementedError

    @abstractmethod
    async def update(self, industry: Industry) -> Industry:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, industry_id: UUID) -> None:
        raise NotImplementedError
