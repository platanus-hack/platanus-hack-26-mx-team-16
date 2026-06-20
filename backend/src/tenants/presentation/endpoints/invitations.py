"""Public invitation endpoints — token lookup + single-use redemption."""

from __future__ import annotations

from fastapi import status
from pydantic import Field

from src.auth.presentation.presenters.session import (
    TenantUserSessionPresenter,
)
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.infrastructure.dependencies.common import (
    DomainContextDep,
)
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.tenants.application.use_cases.invitations.accept_invitation import (
    AcceptInvitation,
)
from src.tenants.application.use_cases.invitations.get_invitation import (
    GetInvitation,
)
from src.tenants.presentation.presenters.tenant_user_invitation import (
    InvitationViewPresenter,
)


class AcceptInvitationRequest(CamelCaseRequest):
    password: str | None = Field(default=None, min_length=8, max_length=128)
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)


async def get_invitation_by_token(
    token: str,
    domain_context: DomainContextDep,
) -> ApiJSONResponse:
    view = await GetInvitation(
        token=token,
        tenant_user_invitation_repository=domain_context.tenant_user_invitation_repository,
        tenant_repository=domain_context.tenant_repository,
        tenant_role_repository=domain_context.tenant_role_repository,
    ).execute()

    return ApiJSONResponse(
        content=InvitationViewPresenter(instance=view).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def accept_invitation(
    token: str,
    request: AcceptInvitationRequest,
    domain_context: DomainContextDep,
) -> ApiJSONResponse:
    session = await AcceptInvitation(
        token=token,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name,
        tenant_user_invitation_repository=domain_context.tenant_user_invitation_repository,
        tenant_repository=domain_context.tenant_repository,
        tenant_role_repository=domain_context.tenant_role_repository,
        tenant_user_repository=domain_context.tenant_user_repository,
        user_repository=domain_context.user_repository,
        email_repository=domain_context.email_repository,
        token_service=domain_context.token_service,
    ).execute()

    return ApiJSONResponse(
        content=TenantUserSessionPresenter(instance=session).to_dict,
        status_code=status.HTTP_200_OK,
    )
