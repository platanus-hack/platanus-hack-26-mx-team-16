from typing import TYPE_CHECKING

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin
from src.common.domain.enums.tenants import TenantRoleStatus

if TYPE_CHECKING:
    from src.common.database.models import TenantORM


class TenantRoleORM(Base, UUIDTenantTimestampMixin):
    __tablename__ = "tenant_roles"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_tenant_role_tenant_slug"),)

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(25),
        nullable=False,
        default=str(TenantRoleStatus.ACTIVE),
        comment="Status",
    )
    icon_url: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    permissions: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="[]",
    )

    # -> Relationships
    tenant: Mapped["TenantORM"] = relationship(
        back_populates=None,
    )
