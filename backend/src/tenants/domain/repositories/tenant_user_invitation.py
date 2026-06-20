from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.models.tenants.tenant_user_invitation import (
    TenantUserInvitation,
)


class TenantUserInvitationRepository(ABC):
    @abstractmethod
    async def persist(self, invitation: TenantUserInvitation) -> TenantUserInvitation:
        raise NotImplementedError

    @abstractmethod
    async def persist_many(self, invitations: list[TenantUserInvitation]) -> list[TenantUserInvitation]:
        raise NotImplementedError

    @abstractmethod
    async def find_by_token(self, token: str) -> TenantUserInvitation | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, invitation_id: UUID) -> TenantUserInvitation | None:
        raise NotImplementedError

    @abstractmethod
    async def list_pending_by_tenant(self, tenant_id: UUID) -> list[TenantUserInvitation]:
        raise NotImplementedError

    @abstractmethod
    async def mark_accepted(self, invitation_id: UUID) -> TenantUserInvitation:
        raise NotImplementedError

    @abstractmethod
    async def mark_expired(self, invitation_id: UUID) -> TenantUserInvitation:
        raise NotImplementedError

    @abstractmethod
    async def rotate_token(self, invitation_id: UUID, new_token: str) -> TenantUserInvitation:
        raise NotImplementedError
