"""Shared "invite N members to a tenant" use case.

Both the `TenantOnboarder` (Register Tenant wizard) and the `/members`
screen end up doing the same thing: for each invited email, create a
`TenantUserInvitation` row (skipping users that are already members)
and dispatch a templated email to the recipient. This module owns that
logic so the two callers don't diverge over time.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from src.common.application.commands.common import SendEmailCommand
from src.common.domain.buses.commands import CommandBus
from src.common.domain.enums.tenants import TenantUserInvitationStatus
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user_invitation import (
    TenantUserInvitation,
)
from src.common.settings import settings
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository
from src.tenants.domain.repositories.tenant_user import TenantUserRepository
from src.tenants.domain.repositories.tenant_user_invitation import (
    TenantUserInvitationRepository,
)
from src.users.domain.repositories.user import UserRepository

INVITATION_TTL = timedelta(days=7)


@dataclass
class MemberInvitationInput:
    email: str
    role_slug: str  # e.g. "admin" | "member"


@dataclass
class SkippedExistingMember:
    """A member that was not invited because the underlying user is
    already an active `TenantUser` of the target tenant."""

    email: str


@dataclass
class InviteMembersResult:
    invitations: list[TenantUserInvitation]
    skipped_existing_members: list[SkippedExistingMember]


@dataclass
class InviteTenantMembers(UseCase):
    tenant: Tenant
    members: list[MemberInvitationInput]
    invited_by_user_id: uuid.UUID
    command_bus: CommandBus
    tenant_user_invitation_repository: TenantUserInvitationRepository
    tenant_user_repository: TenantUserRepository
    tenant_role_repository: TenantRoleRepository
    user_repository: UserRepository
    skip_email: bool = False
    invite_base_url: str = field(default_factory=lambda: settings.FRONTEND_HOST or "http://localhost:3000")

    async def execute(self) -> InviteMembersResult:
        invitations, skipped = await self._create_invitations()
        if invitations and not self.skip_email:
            await self._dispatch_invitation_emails(invitations)
        return InviteMembersResult(
            invitations=invitations,
            skipped_existing_members=skipped,
        )

    async def _create_invitations(
        self,
    ) -> tuple[list[TenantUserInvitation], list[SkippedExistingMember]]:
        if not self.members:
            return [], []

        roles_by_slug: dict[str, object] = {}
        now = datetime.now(UTC)
        drafts: list[TenantUserInvitation] = []
        skipped: list[SkippedExistingMember] = []

        for member in self.members:
            email = member.email.strip().lower()
            existing_user = await self.user_repository.find_by_email(email)
            if existing_user is not None:
                already_member = await self.tenant_user_repository.find_by_args(
                    user_id=existing_user.uuid,
                    tenant_id=self.tenant.uuid,
                )
                if already_member is not None:
                    skipped.append(SkippedExistingMember(email=email))
                    continue

            if member.role_slug not in roles_by_slug:
                roles_by_slug[member.role_slug] = await self.tenant_role_repository.find_by_slug(
                    tenant_id=self.tenant.uuid,
                    slug=member.role_slug,
                )
            role = roles_by_slug[member.role_slug]
            drafts.append(
                TenantUserInvitation(
                    uuid=uuid.uuid4(),
                    tenant_id=self.tenant.uuid,
                    email=email,
                    tenant_role_id=role.uuid if role else None,  # type: ignore[attr-defined]
                    token=_new_invitation_token(),
                    status=TenantUserInvitationStatus.PENDING,
                    expires_at=now + INVITATION_TTL,
                    created_by_id=self.invited_by_user_id,
                    requires_password=existing_user is None,
                )
            )

        invitations: list[TenantUserInvitation] = []
        if drafts:
            invitations = await self.tenant_user_invitation_repository.persist_many(drafts)
        return invitations, skipped

    async def _dispatch_invitation_emails(
        self,
        invitations: list[TenantUserInvitation],
    ) -> None:
        for invitation in invitations:
            invitation_url = f"{self.invite_base_url.rstrip('/')}/invitations/{invitation.token}"
            await self.command_bus.dispatch(
                command=SendEmailCommand(
                    to_emails=[invitation.email],
                    subject=f"Invitación para unirte a {self.tenant.name}",
                    template_name="invitation",
                    context={
                        "name": invitation.email,
                        "tenant_name": self.tenant.name,
                        "invitation_url": invitation_url,
                    },
                ),
            )


def _new_invitation_token() -> str:
    """URL-safe single-use token. 32 bytes → ~43 chars base64."""
    return secrets.token_urlsafe(32)
