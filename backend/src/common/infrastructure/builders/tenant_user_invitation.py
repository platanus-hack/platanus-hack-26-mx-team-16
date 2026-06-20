from src.common.database.models.tenants.tenant_user_invitation import (
    TenantUserInvitationORM,
)
from src.common.domain.enums.tenants import TenantUserInvitationStatus
from src.common.domain.models.tenants.tenant_user_invitation import (
    TenantUserInvitation,
)


def build_tenant_user_invitation(
    orm_instance: TenantUserInvitationORM,
) -> TenantUserInvitation:
    return TenantUserInvitation(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        email=orm_instance.email,
        tenant_role_id=orm_instance.tenant_role_id,
        token=orm_instance.token,
        status=TenantUserInvitationStatus(orm_instance.status),
        expires_at=orm_instance.expires_at,
        accepted_at=orm_instance.accepted_at,
        created_by_id=orm_instance.created_by_id,
        requires_password=orm_instance.requires_password,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
