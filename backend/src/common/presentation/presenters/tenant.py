from dataclasses import dataclass
from typing import Any

from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.interfaces.presenter import Presenter


@dataclass
class AdminTenantPresenter(Presenter[Tenant]):
    instance: Tenant

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "name": self.instance.name,
            "slug": self.instance.slug,
            "time_zone": self.instance.time_zone,
            "country_code": self.instance.country_code,
            "currency_code": self.instance.currency_code,
        }
