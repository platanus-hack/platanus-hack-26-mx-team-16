from src.common.database.models.tenants.tenant_user import TenantUserORM
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.enums.users import TenantUserStatus
from src.common.infrastructure.builders.tenants.tenant import build_tenant
from src.common.infrastructure.builders.tenants.tenant_role import build_tenant_role
from src.common.infrastructure.builders.user import build_user


def build_tenant_user(
    orm_instance: TenantUserORM,
) -> TenantUser:
    return TenantUser(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        user_id=orm_instance.user_id,
        user=build_user(orm_instance.user),
        tenant=build_tenant(orm_instance.tenant),
        is_owner=orm_instance.is_owner,
        is_support=orm_instance.is_support or False,
        status=TenantUserStatus.from_value(orm_instance.status),
        first_name=orm_instance.first_name,
        last_name=orm_instance.last_name,
        tenant_role_id=orm_instance.tenant_role_id,
        tenant_role=build_tenant_role(orm_instance.tenant_role) if orm_instance.tenant_role else None,
        permissions=orm_instance.permissions or [],
        photo=orm_instance.photo,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
