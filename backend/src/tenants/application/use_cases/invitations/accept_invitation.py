"""Single-use redemption of a tenant invitation.

Flow:
1. Look up the invitation by token and validate state. Three distinct
   exceptions surface to the API so the frontend can render the right
   message (not found / already accepted / expired).
2. Get-or-create the `User` keyed by email. Existing users are reused
   as-is — name, password and other personal data on the `User` are
   never overwritten by an invitation.
3. Set the password only when the invitation requires it (i.e. it was
   created for an email that had no `User` at invitation time). Even if
   the flag says otherwise, an existing user with a password is never
   overwritten — defensive guard against TOCTOU between invite + accept.
4. Get-or-create the `TenantUser` row for `(user, tenant)` with the
   invitation's role. The first/last name captured by the form is
   persisted on the `TenantUser` (per-tenant display name), never on
   the shared `User`.
5. Update the user's `current_tenant_id` so the landing page shows the
   tenant they just joined.
6. Mark the invitation `ACCEPTED` so the token cannot be reused.
7. Return a freshly-issued `TenantUserSession` for the browser.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from src.common.domain.entities.auth.user_session import TenantUserSession
from src.common.domain.enums.users import TenantUserStatus
from src.common.domain.exceptions.tenants import (
    InvitationAlreadyAcceptedError,
    InvitationExpiredError,
    InvitationNotFoundError,
    InvitationPasswordRequiredError,
)
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.models.user import User
from src.common.domain.services.token_service import TokenService
from src.tenants.domain.repositories.tenant import TenantRepository
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository
from src.tenants.domain.repositories.tenant_user import TenantUserRepository
from src.tenants.domain.repositories.tenant_user_invitation import (
    TenantUserInvitationRepository,
)
from src.users.domain.repositories.email_address import EmailAddressRepository
from src.users.domain.repositories.user import UserRepository


@dataclass
class AcceptInvitation(UseCase):
    token: str
    password: str | None
    first_name: str | None
    last_name: str | None
    tenant_user_invitation_repository: TenantUserInvitationRepository
    tenant_repository: TenantRepository
    tenant_role_repository: TenantRoleRepository
    tenant_user_repository: TenantUserRepository
    user_repository: UserRepository
    email_repository: EmailAddressRepository
    token_service: TokenService

    async def execute(self) -> TenantUserSession:
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

        existing_user = await self.user_repository.find_by_email(invitation.email)

        # Validate password BEFORE creating any rows so a missing
        # password cannot leave an orphan `User` behind. The flag on the
        # invitation is the contract with the form, but we re-check the
        # `User` existence: if a `User` already has a password (e.g. the
        # email signed up between invite and accept), we never overwrite
        # it — defensive guard against TOCTOU.
        needs_password = invitation.requires_password and existing_user is None
        if needs_password and not self.password:
            raise InvitationPasswordRequiredError

        user = existing_user or await self._create_user(invitation.email)
        if needs_password:
            await self.user_repository.set_password(user_id=user.uuid, new_password=self.password)

        await self._ensure_tenant_user(
            user=user,
            tenant_id=tenant.uuid,
            invitation_role_id=invitation.tenant_role_id,
        )
        await self.user_repository.update_current_tenant(user_id=user.uuid, tenant_id=tenant.uuid)
        await self.tenant_user_invitation_repository.mark_accepted(invitation.uuid)

        tenant_user = await self.tenant_user_repository.find_by_args(
            user_id=user.uuid,
            tenant_id=tenant.uuid,
        )
        tenant_role = tenant_user.tenant_role_meta if tenant_user else None

        jwt_session = await self.token_service.generate_token(
            sub=str(user.uuid),
            namespace="USER",
        )
        return TenantUserSession(
            session=jwt_session,
            user=user,
            tenant=tenant,
            tenant_user=tenant_user,
            tenant_role=tenant_role,
        )

    async def _create_user(self, email: str) -> User:
        email_address = await self.email_repository.get_or_create(email)
        draft = User(
            uuid=uuid.uuid4(),
            username=email,
            email_address=email_address,
        )
        # First/last name live on `TenantUser`; `User` stays minimal.
        # A throwaway password is set if the invitation does not require
        # one — the account can still be used (the user will sign in via
        # password reset or SSO down the line).
        seed_password = self.password or secrets.token_urlsafe(32)
        return await self.user_repository.create_user(
            user=draft,
            password=seed_password,
        )

    async def _ensure_tenant_user(
        self,
        user: User,
        tenant_id: uuid.UUID,
        invitation_role_id: uuid.UUID | None,
    ) -> TenantUser:
        existing = await self.tenant_user_repository.find_by_args(
            user_id=user.uuid,
            tenant_id=tenant_id,
        )
        if existing is not None:
            existing.tenant_role_id = invitation_role_id
            existing.status = TenantUserStatus.ACTIVE
            if self.first_name:
                existing.first_name = self.first_name
            if self.last_name:
                existing.last_name = self.last_name
            return await self.tenant_user_repository.persist(existing)

        draft = TenantUser(
            uuid=uuid.uuid4(),
            user_id=user.uuid,
            tenant_id=tenant_id,
            is_owner=False,
            is_support=False,
            status=TenantUserStatus.ACTIVE,
            tenant_role_id=invitation_role_id,
            first_name=self.first_name,
            last_name=self.last_name,
        )
        return await self.tenant_user_repository.persist(draft)
