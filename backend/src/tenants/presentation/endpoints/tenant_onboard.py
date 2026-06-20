"""Superuser-only endpoint that creates a tenant, seeds default roles,
adds the calling superuser as `is_support`, and dispatches invitation
emails to the listed members.
"""

from __future__ import annotations

from fastapi import status
from pydantic import BaseModel, EmailStr, Field

from src.auth.presentation.presenters.session import TenantPublicPresenter
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.enums.countries import CountryIsoCode
from src.common.infrastructure.dependencies.common import (
    BusContextDep,
    DomainContextDep,
)
from src.common.infrastructure.dependencies.session import AuthenticatedSuperuserDep
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.tenants.application.use_cases.tenant.onboarder import (
    OnboardingMemberInput,
    TenantOnboarder,
)
from src.tenants.presentation.presenters.tenant_user_invitation import (
    TenantUserInvitationPresenter,
)


class OnboardingMemberRequest(BaseModel):
    email: EmailStr
    role_slug: str = Field(default="member", min_length=1)


class OnboardTenantRequest(CamelCaseRequest):
    name: str = Field(min_length=1, max_length=150)
    country_code: CountryIsoCode = Field(default=CountryIsoCode.MEXICO)
    members: list[OnboardingMemberRequest] = Field(default_factory=list)
    skip_email: bool = Field(default=False)


async def onboard_tenant(
    request: OnboardTenantRequest,
    domain_context: DomainContextDep,
    bus_context: BusContextDep,
    current_user: AuthenticatedSuperuserDep,
) -> ApiJSONResponse:
    result = await TenantOnboarder(
        name=request.name,
        owner=current_user,
        country_code=request.country_code,
        members=[OnboardingMemberInput(email=str(m.email), role_slug=m.role_slug) for m in request.members],
        skip_email=request.skip_email,
        command_bus=bus_context.command_bus,
        tenant_repository=domain_context.tenant_repository,
        tenant_role_repository=domain_context.tenant_role_repository,
        tenant_user_repository=domain_context.tenant_user_repository,
        tenant_user_invitation_repository=domain_context.tenant_user_invitation_repository,
        user_repository=domain_context.user_repository,
    ).execute()

    return ApiJSONResponse(
        content={
            "tenant": TenantPublicPresenter(result.tenant).to_dict,
            "invitations": [TenantUserInvitationPresenter(instance=inv).to_dict for inv in result.invitations],
            "skipped_existing_members": [{"email": m.email} for m in result.skipped_existing_members],
        },
        status_code=status.HTTP_201_CREATED,
    )
