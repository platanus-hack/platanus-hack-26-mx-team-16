from typing import Any

from pydantic import Field

from src.common.domain.entities.mixins.common import BaseModelMixin, TimestampMixin
from src.common.domain.entities.mixins.tenants import TenantMixin
from src.common.domain.entities.tenants.tenant_role import TenantRoleMeta
from src.common.domain.enums.tenants import TenantRoleStatus


class TenantRole(
    BaseModelMixin,
    TenantRoleMeta,
    TenantMixin,
    TimestampMixin,
):
    name: str
    status: TenantRoleStatus
    slug: str
    permissions: list[str] = Field(default_factory=list)

    @property
    def to_persist_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "slug": self.slug,
            "status": str(self.status),
            "permissions": list(self.permissions),
            "icon_url": self.icon_url,
        }
