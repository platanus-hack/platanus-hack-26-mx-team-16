from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin
from src.common.database.mixins.users import ProfileMixin
from src.common.domain.enums.users import TenantUserStatus

if TYPE_CHECKING:
    from src.common.database.models import TenantORM
    from src.common.database.models.tenants.tenant_role import TenantRoleORM
    from src.common.database.models.user import UserORM


class TenantUserORM(Base, UUIDTenantTimestampMixin, ProfileMixin):
    __tablename__ = "tenant_users"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "tenant_id",
            name="uq_tenant_user_id",
        ),
    )

    is_owner: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_support: Mapped[bool | None] = mapped_column(
        Boolean,
        default=False,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(25),
        nullable=False,
        default=TenantUserStatus.ACTIVE,
        comment="Status",
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_role_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("tenant_roles.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    permissions: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        server_default="[]",
    )

    # -> Relationships
    user: Mapped["UserORM"] = relationship(
        back_populates=None,
    )
    tenant: Mapped["TenantORM"] = relationship(
        back_populates=None,
    )
    tenant_role: Mapped[Optional["TenantRoleORM"]] = relationship(
        back_populates=None,
    )

    @property
    def is_active(self) -> bool:
        return bool(self.status == TenantUserStatus.ACTIVE)

    def __repr__(self) -> str:
        return f"<TenantUser {self.display_name} @ Tenant {self.tenant_id}>"

    def __str__(self) -> str:
        return f"{self.display_name} ({self.user.username if self.user else 'Unknown'})"
