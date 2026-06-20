from uuid import UUID

from fastapi import Depends, status
from pydantic import BaseModel

from src.common.domain.contexts.domain import DomainContext
from src.common.domain.entities.common.task_result import TaskResult
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.enums.tenants import TenantRoleStatus
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.tenant_role import TenantRolePermission
from src.common.infrastructure.dependencies.common import get_domain_context
from src.common.infrastructure.dependencies.tenant import get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.tenants.application.use_cases.role.deleter import TenantRoleDeleter
from src.tenants.application.use_cases.role.getter import TenantRoleGetter
from src.tenants.application.use_cases.role.updater import TenantRoleUpdater
from src.tenants.presentation.presenters.tenant_role import TenantRolePresenter


async def get_tenant_role(
    role_id: UUID,
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    domain_context: DomainContext = Depends(get_domain_context),
):
    check_tenant_permission(current_tenant_user, permissions=[TenantRolePermission.view])

    tenant_role = await TenantRoleGetter(
        tenant_role_id=role_id,
        role_repository=domain_context.tenant_role_repository,
    ).execute()

    return ApiJSONResponse(
        content=TenantRolePresenter(tenant_role).to_dict,
        status_code=status.HTTP_200_OK,
    )


class UpdateTenantRole(BaseModel):
    name: str | None = None
    permissions: list[str] | None = None
    status: TenantRoleStatus | None = None
    icon_url: str | None = None


async def update_tenant_role(
    role_id: UUID,
    request: UpdateTenantRole,
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    domain_context: DomainContext = Depends(get_domain_context),
):
    check_tenant_permission(current_tenant_user, permissions=[TenantRolePermission.update])

    tenant_role = await TenantRoleUpdater(
        tenant_role_id=role_id,
        payload=request.model_dump(exclude_none=True, exclude_unset=True),
        role_repository=domain_context.tenant_role_repository,
    ).execute()

    return ApiJSONResponse(
        content=TenantRolePresenter(tenant_role).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def delete_tenant_role(
    role_id: UUID,
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    domain_context: DomainContext = Depends(get_domain_context),
):
    check_tenant_permission(current_tenant_user, permissions=[TenantRolePermission.delete])

    await TenantRoleDeleter(
        tenant_role_id=role_id,
        role_repository=domain_context.tenant_role_repository,
    ).execute()

    return ApiJSONResponse(
        content=TaskResult.success(),
        status_code=status.HTTP_200_OK,
    )
