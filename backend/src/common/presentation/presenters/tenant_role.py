from dataclasses import dataclass
from typing import Any

from src.common.domain.entities.tenants.tenant_role import TenantRoleMeta
from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.permissions.catalog import permissions_to_list_dict


@dataclass
class TenantMetaRolePresenter(Presenter[TenantRole]):
    instance: TenantRoleMeta

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.instance.name,
            "status": str(self.instance.status),
            "is_owner": self.instance.is_owner,
            "permissions": permissions_to_list_dict(self.instance.permissions),
        }
