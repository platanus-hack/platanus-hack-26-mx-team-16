from uuid import UUID

from fastapi import Depends, status

from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.tenant_settings import TenantSettingPermission
from src.common.infrastructure.dependencies.tenant import get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.tenants.presentation.presenters.tenant_settings import TenantSettingsPresenter


async def get_tenant_settings(
    tenant_id: UUID,
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[TenantSettingPermission.view])

    return ApiJSONResponse(
        content=TenantSettingsPresenter(current_tenant_user.tenant).to_dict,
        status_code=status.HTTP_200_OK,
    )
