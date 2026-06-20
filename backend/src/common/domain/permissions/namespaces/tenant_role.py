class TenantRolePermission:
    namespace: str = "tenant_roles"

    view: str = "tenant_roles.view"
    create: str = "tenant_roles.create"
    update: str = "tenant_roles.update"
    delete: str = "tenant_roles.delete"
    assign: str = "tenant_roles.assign"
