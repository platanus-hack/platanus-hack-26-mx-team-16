from typing import Any
from uuid import UUID

from pydantic import Field

from src.common.domain.models.email_address import EmailAddress
from src.common.domain.entities.mixins.common import BaseModelMixin, TimestampMixin
from src.common.domain.entities.mixins.tenants import TenantMixin
from src.common.domain.models.phone_number import PhoneNumber
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.entities.tenants.tenant_role import TenantRoleMeta
from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.models.user import User
from src.common.domain.enums.users import TenantUserStatus
from src.common.domain.enums.tenants import TenantRoleStatus


class TenantUser(
    BaseModelMixin,
    TimestampMixin,
    TenantMixin,
):
    user_id: UUID
    is_owner: bool
    status: TenantUserStatus
    first_name: str | None = Field(default=None)
    last_name: str | None = Field(default=None)
    tenant_role_id: UUID | None = Field(default=None)

    permissions: list[str] = Field(default_factory=list)

    user: User | None = Field(default=None)
    tenant: Tenant | None = Field(default=None)
    tenant_role: TenantRole | None = Field(default=None)
    is_support: bool = Field(default=False)
    # Stored URL for the per-member profile photo. The column name in the
    # ORM is `photo` (inherited from ProfileMixin); we keep the same key
    # in the domain so persist_dict can map straight through.
    photo: str | None = Field(default=None)

    @property
    def display_first_name(self) -> str | None:
        if self.first_name:
            return self.first_name
        if self.user:
            return self.user.first_name
        return None

    @property
    def display_last_name(self) -> str | None:
        if self.last_name:
            return self.last_name
        if self.user:
            return self.user.last_name
        return None

    @property
    def phone_number(self) -> PhoneNumber | None:
        if self.user:
            return self.user.phone_number
        return None

    @property
    def email_address(self) -> EmailAddress | None:
        if self.user:
            return self.user.email_address
        return None

    @property
    def is_active(self) -> bool:
        return self.status == TenantUserStatus.ACTIVE

    @property
    def tenant_role_meta(self) -> TenantRoleMeta | None:
        if self.is_owner:
            return TenantRoleMeta.owner()

        direct_permissions = self.permissions or []

        if not self.tenant_role:
            return TenantRoleMeta(
                name="Anonymous",
                slug="anonymous",
                status=TenantRoleStatus.ACTIVE,
                is_owner=False,
                permissions=direct_permissions,
            )

        role_permissions = self.tenant_role.permissions or []

        return TenantRoleMeta(
            name=self.tenant_role.name,
            status=self.tenant_role.status,
            slug=self.tenant_role.slug,
            is_owner=False,
            permissions=list(set(role_permissions + direct_permissions)),
        )

    @property
    def tenant_id(self) -> UUID | None:
        return self.tenant.uuid if self.tenant else None

    @property
    def mixed_permissions(self) -> list[str]:
        user_permissions = self.permissions or []
        tenant_role_meta = self.tenant_role_meta
        if not tenant_role_meta:
            return user_permissions
        role_permissions = tenant_role_meta.permissions or []
        return list(set(user_permissions + role_permissions))

    @property
    def to_persist_dict(self) -> dict[str, Any]:
        return {
            "uuid": self.uuid,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "status": str(self.status),
            "is_owner": self.is_owner,
            "is_support": self.is_support,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "tenant_role_id": self.tenant_role_id,
            "permissions": self.permissions,
            "photo": self.photo,
        }

    def check_permission(self, permission: str) -> bool:
        if not self.is_active or not permission or not self.tenant_role_meta:
            return False

        if self.tenant_role_meta.is_owner:
            return True

        return permission in self.mixed_permissions

    def check_permissions(self, permissions: list[str]) -> bool:
        if not self.is_active or not permissions or not self.tenant_role_meta:
            return False

        if self.tenant_role_meta.is_owner:
            return True

        return all(permission in self.mixed_permissions for permission in permissions)
