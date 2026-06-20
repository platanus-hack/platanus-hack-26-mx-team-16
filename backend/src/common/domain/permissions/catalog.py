from typing import Any

from src.common.domain.permissions.namespaces.connection import ConnectionPermission
from src.common.domain.permissions.namespaces.dashboard import DashboardPermission
from src.common.domain.permissions.namespaces.tenant_role import TenantRolePermission
from src.common.domain.permissions.namespaces.tenant_settings import TenantSettingPermission
from src.common.domain.permissions.namespaces.tenant_user import TenantUserPermission
from src.common.domain.permissions.namespaces.workflow import WorkflowPermission

PERMISSIONS_CATALOG: dict[Any, str] = {
    # Dashboard
    DashboardPermission.view: "Ver dashboard",
    # Tenant Roles
    TenantRolePermission.view: "Ver roles",
    TenantRolePermission.create: "Crear roles",
    TenantRolePermission.update: "Actualizar roles",
    TenantRolePermission.delete: "Eliminar roles",
    TenantRolePermission.assign: "Asignar roles",
    # Tenant Users
    TenantUserPermission.view: "Ver usuarios",
    TenantUserPermission.create: "Crear usuarios",
    TenantUserPermission.update: "Actualizar usuarios",
    TenantUserPermission.delete: "Eliminar usuarios",
    # Settings
    TenantSettingPermission.view: "Ver configuraciones",
    TenantSettingPermission.update: "Actualizar configuraciones",
    TenantSettingPermission.delete: "Eliminar organizacion",
    # Workflows
    WorkflowPermission.view: "Ver workflows",
    WorkflowPermission.create: "Crear workflows",
    WorkflowPermission.update: "Actualizar workflows",
    WorkflowPermission.delete: "Eliminar workflows",
    WorkflowPermission.view_usage: "Ver uso de workflows",
    WorkflowPermission.add_integration: "Agregar integración a workflows",
    # Connections (org-level connection accounts)
    ConnectionPermission.manage: "Gestionar conexiones",
}
FULL_PERMISSIONS = list(PERMISSIONS_CATALOG.keys())


def get_permission_label(permission_code: str) -> str:
    return PERMISSIONS_CATALOG.get(permission_code, "Permiso desconocido")


def permission_to_dict(permission_code: str) -> dict[str, str]:
    return {
        "code": permission_code,
        "label": get_permission_label(permission_code),
    }


def permissions_to_list_dict(permission_codes: list[str]) -> list[dict[str, str]]:
    return [permission_to_dict(code) for code in permission_codes]
