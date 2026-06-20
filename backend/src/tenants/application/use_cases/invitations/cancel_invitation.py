"""Cancel a pending invitation.

We reuse the `EXPIRED` status (instead of introducing a `CANCELED` one)
so the public landing page renders the same "Esta invitación caducó"
message — the invited user doesn't need to distinguish between the two
cases. It also re-opens the partial unique index on `(tenant_id, email)
WHERE status='PENDING'`, so an admin can re-invite the same email
immediately.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.exceptions.tenants import (
    InvitationAlreadyAcceptedError,
    InvitationNotFoundError,
)
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.tenants.tenant_user_invitation import (
    TenantUserInvitation,
)
from src.tenants.domain.repositories.tenant_user_invitation import (
    TenantUserInvitationRepository,
)


@dataclass
class CancelInvitation(UseCase):
    invitation_id: UUID
    tenant_id: UUID
    tenant_user_invitation_repository: TenantUserInvitationRepository

    async def execute(self) -> TenantUserInvitation:
        invitation = await self.tenant_user_invitation_repository.find_by_id(
            self.invitation_id,
        )
        # Tenant scoping: a 404 on cross-tenant access avoids leaking
        # invitation ids across tenants.
        if invitation is None or invitation.tenant_id != self.tenant_id:
            raise InvitationNotFoundError
        if invitation.is_accepted:
            raise InvitationAlreadyAcceptedError

        return await self.tenant_user_invitation_repository.mark_expired(
            invitation.uuid,
        )
