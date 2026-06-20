from dataclasses import dataclass
from typing import Any

from src.common.domain.entities.auth.user_session import TenantUserProfile, TenantUserSession
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.user import User
from src.common.domain.interfaces.presenter import Presenter
from src.common.infrastructure.helpers.statics import get_static_path
from src.common.presentation.presenters.tenant_role import TenantMetaRolePresenter


@dataclass
class UserPresenter(Presenter[User]):
    instance: User
    first_name: str | None = None
    last_name: str | None = None
    photo_url: str | None = None

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "username": self.instance.username,
            "first_name": self.first_name or self.instance.first_name,
            "last_name": self.last_name or self.instance.last_name,
            "phone_number": (self.instance.phone_number.model_dump() if self.instance.phone_number else None),
            "email_address": (self.instance.email_address.model_dump() if self.instance.email_address else None),
            "photo_url": self.photo_url,
            "is_superuser": self.instance.is_superuser,
        }


class TenantPublicPresenter(Presenter[Tenant]):
    instance: Tenant

    def __init__(self, instance: Tenant):
        self.instance = instance
        super().__init__(instance)  # type: ignore

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "name": self.instance.name,
            "slug": self.instance.slug,
            "time_zone": str(self.instance.time_zone),
            "country_code": str(self.instance.country_code),
            "currency_code": str(self.instance.currency_code),
            "logo_url": (get_static_path(self.instance.logo_url) if self.instance.logo_url else None),
            "status": str(self.instance.status),
        }


@dataclass
class TenantUserSessionPresenter(Presenter[TenantUserSession]):
    instance: TenantUserSession

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "session": self.instance.session.model_dump(),
            "user": UserPresenter(
                instance=self.instance.user,
                first_name=self.instance.display_first_name,
                last_name=self.instance.display_last_name,
                photo_url=self.instance.display_photo,
            ).to_dict,
            "tenant": (TenantPublicPresenter(self.instance.tenant).to_dict if self.instance.tenant else None),
            "tenant_role": (
                TenantMetaRolePresenter(self.instance.tenant_role).to_dict if self.instance.tenant_role else None
            ),
        }


@dataclass
class TenantUserProfilePresenter(Presenter[TenantUserProfile]):
    instance: TenantUserProfile

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "user": UserPresenter(instance=self.instance.user).to_dict,
            "tenant": (TenantPublicPresenter(self.instance.tenant).to_dict if self.instance.tenant else None),
            "tenant_role": (
                TenantMetaRolePresenter(self.instance.tenant_role).to_dict if self.instance.tenant_role else None
            ),
        }
