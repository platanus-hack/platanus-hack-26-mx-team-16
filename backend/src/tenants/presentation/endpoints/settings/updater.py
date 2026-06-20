from uuid import UUID

from fastapi import Depends, status
from pydantic import Field

from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.tenant_settings import TenantSettingPermission
from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.tenants.application.use_cases.tenant.updater import TenantUpdater
from src.tenants.presentation.presenters.tenant_settings import TenantSettingsPresenter


class UpdateTenantSettingsRequest(CamelCaseRequest):
    name: str = Field(min_length=1, max_length=150)


async def update_tenant_settings(
    tenant_id: UUID,
    request: UpdateTenantSettingsRequest,
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    domain_context: DomainContextDep = None,
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[TenantSettingPermission.update])

    tenant = await TenantUpdater(
        tenant_id=current_tenant_user.tenant.uuid,
        tenant_repository=domain_context.tenant_repository,
        payload={"name": request.name},
    ).execute()

    return ApiJSONResponse(
        content=TenantSettingsPresenter(tenant).to_dict,
        status_code=status.HTTP_200_OK,
    )
