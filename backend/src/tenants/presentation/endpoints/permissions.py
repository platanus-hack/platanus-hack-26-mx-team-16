from fastapi import Depends, status

from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.catalog import FULL_PERMISSIONS, permissions_to_list_dict
from src.common.infrastructure.dependencies.tenant import get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse


class PermissionPayload(CamelCaseRequest):
    code: str
    label: str | None = None


class PermissionsRequest(CamelCaseRequest):
    permissions: list[PermissionPayload]


async def get_missing_permissions(
    request: PermissionsRequest,
    _tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    received_permissions = {permission.code for permission in request.permissions}
    missing_permissions = sorted(set(FULL_PERMISSIONS) - received_permissions)

    return ApiJSONResponse(
        content=permissions_to_list_dict(missing_permissions),
        status_code=status.HTTP_200_OK,
    )
