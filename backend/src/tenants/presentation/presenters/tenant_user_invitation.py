from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.application.helpers.uuids import optional_string
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.tenants.tenant_user_invitation import (
    TenantUserInvitation,
)


@dataclass
class TenantUserInvitationPresenter(Presenter[TenantUserInvitation]):
    instance: TenantUserInvitation

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": optional_string(self.instance.uuid),
            "tenant_id": optional_string(self.instance.tenant_id),
            "email": self.instance.email,
            "tenant_role_id": optional_string(self.instance.tenant_role_id),
            "token": self.instance.token,
            "status": self.instance.status.value,
            "expires_at": optional_datetime_string(self.instance.expires_at),
            "accepted_at": optional_datetime_string(self.instance.accepted_at),
            "created_by_id": optional_string(self.instance.created_by_id),
            "requires_password": self.instance.requires_password,
            "created_at": optional_datetime_string(self.instance.created_at),
        }


@dataclass
class InvitationViewPresenter(Presenter):
    instance: Any

    @property
    def to_dict(self) -> dict[str, Any]:
        invitation = self.instance.invitation
        return {
            "email": invitation.email,
            "tenant_name": self.instance.tenant_name,
            "role_name": self.instance.role_name,
            "expires_at": optional_datetime_string(invitation.expires_at),
            "requires_password": invitation.requires_password,
        }
