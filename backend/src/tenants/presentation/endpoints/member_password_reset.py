"""Admin endpoint to email a password-reset link to a tenant member.

Wraps :class:`SendPasswordResetToMember` so the `/members` screen can
trigger the link with a meaningful 200/404 response, unlike the public
`/v1/auth/reset-password` endpoint which is anti-enumeration.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Path, status

from src.common.domain.contexts.bus import BusContext
from src.common.domain.contexts.domain import DomainContext
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.tenant_user import TenantUserPermission
from src.common.infrastructure.dependencies.common import (
    get_bus_context,
    get_domain_context,
)
from src.common.infrastructure.dependencies.tenant import get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.tenants.application.use_cases.tenant_user.send_password_reset import (
    SendPasswordResetToMember,
)


async def send_member_password_reset(
    tenant_user_id: UUID = Path(..., description="TenantUser UUID"),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    domain_context: DomainContext = Depends(get_domain_context),
    bus_context: BusContext = Depends(get_bus_context),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[TenantUserPermission.update])

    email = await SendPasswordResetToMember(
        tenant_user_id=tenant_user_id,
        tenant_id=current_tenant_user.tenant_id,
        tenant_user_repository=domain_context.tenant_user_repository,
        user_repository=domain_context.user_repository,
        token_service=domain_context.token_service,
        command_bus=bus_context.command_bus,
    ).execute()

    return ApiJSONResponse(
        content={"email": email},
        status_code=status.HTTP_200_OK,
    )
