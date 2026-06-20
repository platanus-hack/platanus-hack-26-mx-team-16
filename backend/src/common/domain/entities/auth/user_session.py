from pydantic import Field

from src.common.domain.entities.common.jtw_session import JwtSession
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.entities.tenants.tenant_role import TenantRoleMeta
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.models.user import User
from src.common.domain.mixins.entities import CamelModel


class UserSession(CamelModel):
    session: JwtSession
    user: User


class TenantUserProfile(CamelModel):
    user: User
    tenant: Tenant | None = None
    tenant_role: TenantRoleMeta | None = None


class TenantSessionParams(CamelModel):
    tenant: Tenant | None = Field(default=None)
    tenant_user: TenantUser | None = Field(default=None)
    tenant_role: TenantRoleMeta | None = Field(default=None)


class TenantUserSession(TenantUserProfile, TenantSessionParams):
    session: JwtSession
    user: User

    @property
    def display_first_name(self) -> str | None:
        if self.tenant_user:
            return self.tenant_user.first_name
        return self.user.first_name

    @property
    def display_last_name(self) -> str | None:
        if self.tenant_user:
            return self.tenant_user.last_name
        return self.user.last_name

    @property
    def display_photo(self) -> str | None:
        if self.tenant_user and self.tenant_user.photo:
            return self.tenant_user.photo
        return None
