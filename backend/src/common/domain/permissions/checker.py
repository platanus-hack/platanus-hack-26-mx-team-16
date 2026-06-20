from src.common.constants import PERMISSIONS_ENABLED
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.exceptions.permission import InsufficientPermissionsError


def check_tenant_permission(
    tenant_user: TenantUser | None,
    permissions: list[str],
) -> bool:
    if not PERMISSIONS_ENABLED:
        return True

    if not tenant_user or tenant_user.check_permissions(permissions) is False:
        raise InsufficientPermissionsError(permissions=permissions)
    return True
