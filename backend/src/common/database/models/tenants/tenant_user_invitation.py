from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin
from src.common.domain.enums.tenants import TenantUserInvitationStatus


class TenantUserInvitationORM(Base, UUIDTenantTimestampMixin):
    __tablename__ = "tenant_user_invitations"
    __table_args__ = (
        Index("ix_tenant_user_invitations_tenant_id", "tenant_id"),
        # Una sola invitación PENDING por (tenant_id, email) — único parcial.
        Index(
            "uq_tenant_user_invitations_pending_email",
            "tenant_id",
            "email",
            unique=True,
            postgresql_where=text("status = 'PENDING'"),
        ),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    tenant_role_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("tenant_roles.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    token: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(
        String(25),
        nullable=False,
        default=TenantUserInvitationStatus.PENDING.value,
        server_default=TenantUserInvitationStatus.PENDING.value,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    requires_password: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
