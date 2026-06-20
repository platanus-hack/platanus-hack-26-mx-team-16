from src.common.domain.entities.tenants.tenant_role import TenantRoleMeta
from src.common.domain.permissions.catalog import FULL_PERMISSIONS
from src.common.domain.permissions.namespaces.dashboard import DashboardPermission

DEFAULT_TENANT_ROLES = [
    TenantRoleMeta(
        name="Administrador",
        slug="admin",
        permissions=FULL_PERMISSIONS,
    ),
    TenantRoleMeta(
        name="Miembro",
        slug="member",
        permissions=[
            DashboardPermission.view,
        ],
    ),
]
