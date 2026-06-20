from dataclasses import dataclass
from typing import Any

from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.permissions.catalog import permissions_to_list_dict


@dataclass
class TenantRolePresenter(Presenter[TenantRole]):
    instance: TenantRole

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "name": self.instance.name,
            "slug": self.instance.slug,
            "status": str(self.instance.status),
            "permissions": permissions_to_list_dict(self.instance.permissions),
            "icon_url": self.instance.icon_url,
        }


@dataclass
class SimpleTenantRolePresenter(Presenter[TenantRole]):
    instance: TenantRole

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "name": self.instance.name,
            "status": str(self.instance.status),
        }
