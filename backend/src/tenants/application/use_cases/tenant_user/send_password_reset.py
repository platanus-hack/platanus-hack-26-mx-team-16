"""Admin-initiated password reset for a tenant member.

Distinct from the public `POST /v1/auth/reset-password` endpoint:
- That one is anti-enumeration (always 200, silent no-op on unknown
  emails) because it is reachable without auth.
- This one is admin-only and operates on a `tenant_user_id`, so we
  can validate ownership and return a proper 404 / 200. The admin
  needs to know whether the email actually went out.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.auth.application.use_cases.request_password_reset import (
    RequestPasswordReset,
)
from src.common.domain.buses.commands import CommandBus
from src.common.domain.exceptions.users import TenantUserNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.services.token_service import TokenService
from src.tenants.domain.repositories.tenant_user import TenantUserRepository
from src.users.domain.repositories.user import UserRepository


@dataclass
class SendPasswordResetToMember(UseCase):
    tenant_user_id: UUID
    tenant_id: UUID
    tenant_user_repository: TenantUserRepository
    user_repository: UserRepository
    token_service: TokenService
    command_bus: CommandBus

    async def execute(self) -> str:
        """Returns the email the link was sent to so the caller can show
        actionable feedback to the admin."""
        tenant_user = await self.tenant_user_repository.find(self.tenant_user_id)
        if tenant_user is None or tenant_user.tenant_id != self.tenant_id:
            raise TenantUserNotFoundError

        email = tenant_user.email_address.email if tenant_user.email_address else None
        if not email:
            raise TenantUserNotFoundError

        await RequestPasswordReset(
            email=email,
            user_repository=self.user_repository,
            token_service=self.token_service,
            command_bus=self.command_bus,
        ).execute()
        return email
