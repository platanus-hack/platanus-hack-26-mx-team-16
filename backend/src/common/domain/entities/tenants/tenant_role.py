from pydantic import BaseModel, Field

from src.common.domain.enums.tenants import TenantRoleStatus


class TenantRoleMeta(BaseModel):
    name: str
    status: TenantRoleStatus = Field(default=TenantRoleStatus.INACTIVE)
    slug: str = Field(default="")
    is_owner: bool = Field(default=False)
    permissions: list[str] = Field(default_factory=list)
    icon_url: str | None = None

    @classmethod
    def owner(cls) -> "TenantRoleMeta":
        return cls(
            name="Owner",
            slug="owner",
            status=TenantRoleStatus.ACTIVE,
            is_owner=True,
            permissions=[],
        )

    @classmethod
    def anonymous(cls) -> "TenantRoleMeta":
        return cls(
            name="Anonymous",
            slug="anonymous",
            status=TenantRoleStatus.ACTIVE,
            is_owner=False,
            permissions=[],
        )

    @classmethod
    def staff(cls) -> "TenantRoleMeta":
        return cls(
            name="Staff",
            slug="staff",
            status=TenantRoleStatus.ACTIVE,
            is_owner=False,
            permissions=[],
        )

    def activate(self):
        self.status = TenantRoleStatus.ACTIVE

    def deactivate(self):
        self.status = TenantRoleStatus.INACTIVE
