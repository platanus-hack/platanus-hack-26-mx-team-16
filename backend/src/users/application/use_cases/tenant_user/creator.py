"""Create (or idempotently reuse) a tenant member.

Mirrors the get-or-create flow used by ``AcceptInvitation``: the shared ``User``
is looked up by email and created only when missing (its password/personal data
are never overwritten), then the per-tenant ``TenantUser`` row is created with
the display name + role captured on the form. ``reuse=True`` makes the operation
idempotent — an existing ``(user, tenant)`` pair is returned as-is instead of
raising, so the endpoint answers 200 (reused) vs 201 (created).
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from uuid import UUID

from src.common.domain.enums.users import TenantUserStatus
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.models.user import User
from src.tenants.domain.repositories.tenant_user import TenantUserRepository
from src.users.domain.exceptions import UserAlreadyExistError
from src.users.domain.repositories.email_address import EmailAddressRepository
from src.users.domain.repositories.user import UserRepository


@dataclass
class TenantUserCreationResult:
    tenant_user: TenantUser
    created: bool


@dataclass
class TenantUserCreator(UseCase):
    tenant_id: UUID
    email: str
    password: str | None
    first_name: str | None
    last_name: str | None
    is_owner: bool
    status: TenantUserStatus
    tenant_role_id: UUID | None
    reuse: bool
    tenant_user_repository: TenantUserRepository
    user_repository: UserRepository
    email_repository: EmailAddressRepository

    async def execute(self) -> TenantUserCreationResult:
        user = await self.user_repository.find_by_email(self.email)
        if user is None:
            user = await self._create_user(self.email)

        existing = await self.tenant_user_repository.find_by_args(
            user_id=user.uuid,
            tenant_id=self.tenant_id,
        )
        if existing is not None:
            if not self.reuse:
                raise UserAlreadyExistError
            reloaded = await self.tenant_user_repository.find(existing.uuid)
            return TenantUserCreationResult(tenant_user=reloaded or existing, created=False)

        draft = TenantUser(
            uuid=uuid.uuid4(),
            user_id=user.uuid,
            tenant_id=self.tenant_id,
            is_owner=self.is_owner,
            is_support=False,
            status=self.status,
            tenant_role_id=self.tenant_role_id,
            first_name=self.first_name,
            last_name=self.last_name,
        )
        persisted = await self.tenant_user_repository.persist(draft)
        # Re-fetch so the relationships the presenter reads (user/email/phone/role)
        # are eagerly loaded — ``persist`` returns a row whose ``user`` is detached.
        reloaded = await self.tenant_user_repository.find(persisted.uuid)
        return TenantUserCreationResult(tenant_user=reloaded or persisted, created=True)

    async def _create_user(self, email: str) -> User:
        # First/last name live on ``TenantUser`` (per-tenant display name); the
        # shared ``User`` stays minimal. A throwaway password is seeded when the
        # caller did not provide one (the member can sign in via password reset).
        draft = User.from_raw(email=email)
        seed_password = self.password or secrets.token_urlsafe(32)
        return await self.user_repository.create_user(
            user=draft,
            password=seed_password,
        )
