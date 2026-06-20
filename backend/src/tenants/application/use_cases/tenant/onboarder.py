"""Atomic onboarding flow for a brand-new tenant.

Reuses :class:`TenantRegisterer` to create the tenant + bootstrap default
roles + create the owner's `TenantUser`. On top of that:

- Flips the owner's `TenantUser.is_support` to ``True`` so they keep
  access without being listed in the tenant's `/members` endpoint.
- Delegates to :class:`InviteTenantMembers` to invite the listed members.
  The same use case is used by the `/members` screen so both flows
  produce identical invitation rows + emails.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from src.common.domain.buses.commands import CommandBus
from src.common.domain.enums.countries import CountryIsoCode
from src.common.domain.exceptions.industries import IndustryNotFoundError
from src.common.domain.exceptions.tenants import TenantNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user_invitation import (
    TenantUserInvitation,
)
from src.common.domain.models.user import User
from src.common.settings import settings
from src.industries.domain.repositories.industry_repository import IndustryRepository
from src.tenants.application.use_cases.invitations.invite_members import (
    InviteTenantMembers,
    MemberInvitationInput,
    SkippedExistingMember,
)
from src.tenants.application.use_cases.tenant.registerer import TenantRegisterer
from src.tenants.domain.repositories.tenant import TenantRepository
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository
from src.tenants.domain.repositories.tenant_user import TenantUserRepository
from src.tenants.domain.repositories.tenant_user_invitation import (
    TenantUserInvitationRepository,
)
from src.users.domain.repositories.user import UserRepository
from src.workflows.domain.repositories.pipeline import PipelineRepository

# Backwards-compatible alias so callers/tests that imported the old name
# from this module keep working until they migrate to `MemberInvitationInput`.
OnboardingMemberInput = MemberInvitationInput


@dataclass
class OnboardingResult:
    tenant: Tenant
    invitations: list[TenantUserInvitation]
    skipped_existing_members: list[SkippedExistingMember]


@dataclass
class TenantOnboarder(UseCase):
    name: str
    owner: User
    country_code: CountryIsoCode
    members: list[MemberInvitationInput]
    command_bus: CommandBus
    tenant_repository: TenantRepository
    tenant_role_repository: TenantRoleRepository
    tenant_user_repository: TenantUserRepository
    tenant_user_invitation_repository: TenantUserInvitationRepository
    user_repository: UserRepository
    industry_repository: IndustryRepository | None = None
    industry_id: uuid.UUID | None = None
    # Siembra la receta standard@v1 del tenant nuevo (E1). Opcional para no
    # romper instanciaciones existentes; el endpoint real SIEMPRE lo wirea.
    pipeline_repository: PipelineRepository | None = None
    skip_email: bool = False
    invite_base_url: str = field(default_factory=lambda: settings.FRONTEND_HOST or "http://localhost:3000")

    async def execute(self) -> OnboardingResult:
        tenant = await TenantRegisterer(
            name=self.name,
            owner=self.owner,
            country_code=self.country_code,
            tenant_repository=self.tenant_repository,
            tenant_role_repository=self.tenant_role_repository,
            command_bus=self.command_bus,
            user_repository=self.user_repository,
            tenant_user_repository=self.tenant_user_repository,
        ).execute()

        await self._mark_owner_as_support(tenant)
        await self._assign_industry_if_any(tenant)
        # ADR 0002: el onboarder ya NO siembra pipelines tenant-level. Cada
        # workflow nace dueño de su pipeline (copy-on-create en WorkflowCreator);
        # las plantillas viven en ``recipes.py`` como código.

        invite_result = await InviteTenantMembers(
            tenant=tenant,
            members=self.members,
            invited_by_user_id=self.owner.uuid,
            command_bus=self.command_bus,
            tenant_user_invitation_repository=self.tenant_user_invitation_repository,
            tenant_user_repository=self.tenant_user_repository,
            tenant_role_repository=self.tenant_role_repository,
            user_repository=self.user_repository,
            skip_email=self.skip_email,
            invite_base_url=self.invite_base_url,
        ).execute()

        return OnboardingResult(
            tenant=tenant,
            invitations=invite_result.invitations,
            skipped_existing_members=invite_result.skipped_existing_members,
        )

    async def _mark_owner_as_support(self, tenant: Tenant) -> None:
        existing = await self.tenant_user_repository.find_by_args(
            user_id=self.owner.uuid,
            tenant_id=tenant.uuid,
        )
        if existing is None:
            raise TenantNotFoundError(str(tenant.uuid))
        existing.is_support = True
        await self.tenant_user_repository.persist(existing)

    async def _assign_industry_if_any(self, tenant: Tenant) -> None:
        if self.industry_id is None:
            return
        if self.industry_repository is None:
            # Programmer error: caller asked for an industry but did not
            # wire the repository. Fail loud rather than silently drop.
            raise RuntimeError(
                "industry_id was provided but industry_repository is missing",
            )
        industry = await self.industry_repository.find_by_id(self.industry_id)
        if industry is None:
            raise IndustryNotFoundError(str(self.industry_id))
        await self.industry_repository.assign_to_tenant(
            tenant_id=tenant.uuid,
            industry_id=industry.uuid,
        )
