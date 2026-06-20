from dataclasses import dataclass
from typing import Any

from src.common.constants import MAX_PAGES
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.interfaces.presenter import Presenter


@dataclass
class TenantSettingsPresenter(Presenter[Tenant]):
    instance: Tenant

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "name": self.instance.name,
            "tenant_id": self.instance.slug,
            "avatar": self.instance.logo_url,
            "max_pages": MAX_PAGES,
            "webhook_signature_key": self.instance.webhook_signature_key or "",
        }
