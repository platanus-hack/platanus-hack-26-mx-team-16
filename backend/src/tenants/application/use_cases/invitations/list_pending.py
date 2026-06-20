"""List pending (non-expired) invitations for a tenant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.tenants.tenant_user_invitation import (
    TenantUserInvitation,
)
from src.tenants.domain.repositories.tenant_user_invitation import (
    TenantUserInvitationRepository,
)


@dataclass
class ListPendingInvitations(UseCase):
    tenant_id: UUID
    tenant_user_invitation_repository: TenantUserInvitationRepository

    async def execute(self) -> list[TenantUserInvitation]:
        rows = await self.tenant_user_invitation_repository.list_pending_by_tenant(
            self.tenant_id,
        )
        now = datetime.now(UTC)
        return [inv for inv in rows if inv.expires_at > now]
