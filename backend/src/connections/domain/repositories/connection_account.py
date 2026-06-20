from abc import ABC, abstractmethod
from uuid import UUID

from src.connections.domain.models.connection_account import ConnectionAccount


class ConnectionAccountRepository(ABC):
    """Persistence for org-level connection accounts (spec connections §2.1)."""

    @abstractmethod
    async def create(self, account: ConnectionAccount) -> ConnectionAccount:
        raise NotImplementedError

    @abstractmethod
    async def update(self, account: ConnectionAccount) -> ConnectionAccount:
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, account_id: UUID, tenant_id: UUID) -> ConnectionAccount | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID) -> list[ConnectionAccount]:
        """All accounts for the org, newest first (spec §3.2)."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, account_id: UUID, tenant_id: UUID) -> None:
        raise NotImplementedError
