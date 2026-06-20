"""Tenant-scoped admin endpoints for invitations.

All three live together so the contract (request/response shape, error
mapping, permissions) stays consistent between create / list / cancel.
They reuse `InviteTenantMembers`, `ListPendingInvitations`, and
`CancelInvitation` so the business logic is the single source of truth.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Path, status
from pydantic import BaseModel, EmailStr, Field

from src.common.domain.contexts.bus import BusContext
from src.common.domain.contexts.domain import DomainContext
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.exceptions.tenants import TenantNotFoundError
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.tenant_user import TenantUserPermission
from src.common.infrastructure.dependencies.common import (
    get_bus_context,
    get_domain_context,
)
from src.common.infrastructure.dependencies.tenant import get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.tenants.application.use_cases.invitations.cancel_invitation import (
    CancelInvitation,
)
from src.tenants.application.use_cases.invitations.invite_members import (
    InviteTenantMembers,
    MemberInvitationInput,
)
from src.tenants.application.use_cases.invitations.list_pending import (
    ListPendingInvitations,
)
from src.tenants.presentation.presenters.tenant_user_invitation import (
    TenantUserInvitationPresenter,
)


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role_slug: str = Field(default="member", min_length=1)


class InviteMembersRequest(CamelCaseRequest):
    members: list[InviteMemberRequest] = Field(default_factory=list, min_length=1)


async def create_tenant_invitations(
    request: InviteMembersRequest,
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    domain_context: DomainContext = Depends(get_domain_context),
    bus_context: BusContext = Depends(get_bus_context),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[TenantUserPermission.create])

    if current_tenant_user.tenant is None:
        # The dependency already validates the X-Tenant header maps to an
        # active Tenant, so this is defensive.
        raise TenantNotFoundError(str(current_tenant_user.tenant_id))

    result = await InviteTenantMembers(
        tenant=current_tenant_user.tenant,
        members=[MemberInvitationInput(email=str(m.email), role_slug=m.role_slug) for m in request.members],
        invited_by_user_id=current_tenant_user.user_id,
        command_bus=bus_context.command_bus,
        tenant_user_invitation_repository=domain_context.tenant_user_invitation_repository,
        tenant_user_repository=domain_context.tenant_user_repository,
        tenant_role_repository=domain_context.tenant_role_repository,
        user_repository=domain_context.user_repository,
    ).execute()

    return ApiJSONResponse(
        content={
            "invitations": [TenantUserInvitationPresenter(instance=inv).to_dict for inv in result.invitations],
            "skipped_existing_members": [{"email": m.email} for m in result.skipped_existing_members],
        },
        status_code=status.HTTP_201_CREATED,
    )


async def list_tenant_invitations(
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    domain_context: DomainContext = Depends(get_domain_context),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[TenantUserPermission.view])

    invitations = await ListPendingInvitations(
        tenant_id=current_tenant_user.tenant_id,
        tenant_user_invitation_repository=domain_context.tenant_user_invitation_repository,
    ).execute()

    return ApiJSONResponse(
        content=[TenantUserInvitationPresenter(instance=inv).to_dict for inv in invitations],
        status_code=status.HTTP_200_OK,
    )


async def cancel_tenant_invitation(
    invitation_id: UUID = Path(..., description="Invitation UUID"),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    domain_context: DomainContext = Depends(get_domain_context),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[TenantUserPermission.delete])

    invitation = await CancelInvitation(
        invitation_id=invitation_id,
        tenant_id=current_tenant_user.tenant_id,
        tenant_user_invitation_repository=domain_context.tenant_user_invitation_repository,
    ).execute()

    return ApiJSONResponse(
        content=TenantUserInvitationPresenter(instance=invitation).to_dict,
        status_code=status.HTTP_200_OK,
    )
