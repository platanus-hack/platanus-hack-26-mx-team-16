class TenantUserPermission:
    namespace: str = "tenant_users"

    view: str = "tenant_users.view"
    create: str = "tenant_users.create"
    update: str = "tenant_users.update"
    delete: str = "tenant_users.delete"
