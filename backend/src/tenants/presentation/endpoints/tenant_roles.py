from fastapi import Depends, status
from pydantic import BaseModel, Field

from src.common.domain.contexts.domain import DomainContext
from src.common.domain.entities.common.collection import ListFilters
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.enums.tenants import TenantRoleStatus
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.tenant_role import TenantRolePermission
from src.common.infrastructure.dependencies.common import get_domain_context
from src.common.infrastructure.dependencies.tenant import get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.tenants.application.use_cases.role.creator import TenantRoleCreator
from src.tenants.application.use_cases.role.lister import TenantRoleLister
from src.tenants.presentation.presenters.tenant_role import TenantRolePresenter


async def get_tenant_roles(
    filters: ListFilters = Depends(),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    domain_context: DomainContext = Depends(get_domain_context),
):
    check_tenant_permission(current_tenant_user, permissions=[TenantRolePermission.view])

    current_page = await TenantRoleLister(
        tenant_id=current_tenant_user.tenant.uuid,
        filters=filters,
        role_repository=domain_context.tenant_role_repository,
    ).execute()

    current_page.apply_presenter(TenantRolePresenter)
    return ApiJSONResponse(
        content=current_page,
        status_code=status.HTTP_200_OK,
    )


class CreateTenantRole(BaseModel):
    name: str
    permissions: list[str] = Field(default_factory=list)
    status: TenantRoleStatus = TenantRoleStatus.ACTIVE
    icon_url: str | None = None


async def create_tenant_role(
    request: CreateTenantRole,
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    domain_context: DomainContext = Depends(get_domain_context),
):
    check_tenant_permission(current_tenant_user, permissions=[TenantRolePermission.create])

    tenant_role = await TenantRoleCreator(
        tenant_id=current_tenant_user.tenant.uuid,
        name=request.name,
        status=request.status,
        permissions=request.permissions,
        icon_url=request.icon_url,
        role_repository=domain_context.tenant_role_repository,
        force_creation=True,
    ).execute()

    return ApiJSONResponse(
        content=TenantRolePresenter(tenant_role).to_dict,
        status_code=status.HTTP_201_CREATED,
    )
