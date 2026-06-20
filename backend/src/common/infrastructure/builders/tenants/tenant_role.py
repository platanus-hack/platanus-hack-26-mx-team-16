from src.common.database.models.tenants.tenant_role import TenantRoleORM
from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.enums.tenants import TenantRoleStatus


def build_tenant_role(
    orm_instance: TenantRoleORM,
) -> TenantRole:
    return TenantRole(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        name=orm_instance.name,
        slug=orm_instance.slug,
        status=TenantRoleStatus.from_value(orm_instance.status),
        permissions=list(orm_instance.permissions or []),
        icon_url=orm_instance.icon_url,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
