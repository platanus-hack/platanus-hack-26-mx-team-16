from fastapi import Depends, status

from src.common.domain.contexts.domain import DomainContext
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.infrastructure.dependencies.common import get_domain_context
from src.common.infrastructure.dependencies.tenant import get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.tenants.application.use_cases.role.bootstraper import TenantRolesBootstrapper
from src.tenants.presentation.presenters.tenant_role import TenantRolePresenter


async def bootstrap_tenant_roles(
    tenant_user: TenantUser = Depends(get_required_tenant_user),
    domain_context: DomainContext = Depends(get_domain_context),
):
    tenant_roles = await TenantRolesBootstrapper(
        tenant_id=tenant_user.tenant.uuid,
        role_repository=domain_context.tenant_role_repository,
    ).execute()

    return ApiJSONResponse(
        content={
            "created": len(tenant_roles),
            "roles": [TenantRolePresenter(role).to_dict for role in tenant_roles],
        },
        status_code=status.HTTP_200_OK,
    )
