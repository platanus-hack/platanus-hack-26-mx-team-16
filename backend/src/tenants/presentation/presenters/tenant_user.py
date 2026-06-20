from dataclasses import dataclass
from typing import Any

from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.interfaces.presenter import Presenter
from src.common.presentation.presenters.email_address import EmailAddressPresenter
from src.common.presentation.presenters.phone_number import PhoneNumberPresenter
from src.tenants.presentation.presenters.tenant_role import SimpleTenantRolePresenter


@dataclass
class TenantUserPresenter(Presenter[TenantUser]):
    instance: TenantUser

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "first_name": self.instance.display_first_name,
            "last_name": self.instance.display_last_name,
            "phone_number": (
                PhoneNumberPresenter(self.instance.phone_number).to_dict if self.instance.phone_number else None
            ),
            "email_address": (
                EmailAddressPresenter(self.instance.email_address).to_dict if self.instance.email_address else None
            ),
            "is_owner": self.instance.is_owner,
            "is_support": self.instance.is_support,
            "photo_url": self.instance.photo,
            "status": str(self.instance.status),
            "tenant_role": (
                SimpleTenantRolePresenter(self.instance.tenant_role).to_dict if self.instance.tenant_role else None
            ),
            "created_at": self.instance.created_at,
        }
