from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.models.tenant_api_key import TenantApiKey


class TenantApiKeyRepository(ABC):
    """Persistence for tenant-scoped M2M API keys (F9)."""

    @abstractmethod
    async def create(self, key: TenantApiKey) -> TenantApiKey:
        raise NotImplementedError

    @abstractmethod
    async def find_by_hash(self, key_hash: str) -> TenantApiKey | None:
        """Resolution path: presented key → hash → tenant binding."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID) -> list[TenantApiKey]:
        raise NotImplementedError

    @abstractmethod
    async def revoke(self, key_id: UUID, tenant_id: UUID) -> None:
        raise NotImplementedError
