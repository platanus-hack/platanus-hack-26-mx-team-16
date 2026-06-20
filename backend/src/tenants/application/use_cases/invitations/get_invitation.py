"""Resolve an invitation by its public token.

Returns a lightweight view used by the public landing page (tenant
name + role label + email). Raises three distinct domain exceptions so
the frontend can render specific UI for "not found", "already accepted"
and "expired".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from src.common.domain.exceptions.tenants import (
    InvitationAlreadyAcceptedError,
    InvitationExpiredError,
    InvitationNotFoundError,
)
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.tenants.tenant_user_invitation import (
    TenantUserInvitation,
)
from src.tenants.domain.repositories.tenant import TenantRepository
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository
from src.tenants.domain.repositories.tenant_user_invitation import (
    TenantUserInvitationRepository,
)


@dataclass
class InvitationView:
    invitation: TenantUserInvitation
    tenant_name: str
    role_name: str | None


@dataclass
class GetInvitation(UseCase):
    token: str
    tenant_user_invitation_repository: TenantUserInvitationRepository
    tenant_repository: TenantRepository
    tenant_role_repository: TenantRoleRepository

    async def execute(self) -> InvitationView:
        invitation = await self.tenant_user_invitation_repository.find_by_token(self.token)
        if invitation is None:
            raise InvitationNotFoundError
        if invitation.is_accepted:
            raise InvitationAlreadyAcceptedError
        if not invitation.is_pending or invitation.expires_at <= datetime.now(UTC):
            raise InvitationExpiredError

        tenant = await self.tenant_repository.find(invitation.tenant_id)
        if tenant is None:
            raise InvitationNotFoundError

        role_name: str | None = None
        if invitation.tenant_role_id is not None:
            role = await self.tenant_role_repository.find(invitation.tenant_role_id)
            role_name = role.name if role else None

        return InvitationView(
            invitation=invitation,
            tenant_name=tenant.name,
            role_name=role_name,
        )
