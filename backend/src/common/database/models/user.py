from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.common.database.mixins.common import Base, UUIDTimestampMixin
from src.common.database.mixins.users import PersonMixin

if TYPE_CHECKING:
    from src.common.database.models.email_address import EmailAddressORM
    from src.common.database.models.phone_number import PhoneNumberORM
    from src.common.database.models.tenants.tenant import TenantORM


class UserORM(Base, UUIDTimestampMixin, PersonMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email_address_id", name="uq_users_email_address_id"),
        UniqueConstraint("phone_number_id", name="uq_users_phone_number_id"),
    )

    username: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        index=True,
    )
    password: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Hashed password",
    )

    email_address_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("email_addresses.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    phone_number_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("phone_numbers.uuid", ondelete="SET NULL"),
        nullable=True,
    )

    current_tenant_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "tenants.uuid",
            ondelete="SET NULL",
            deferrable=True,
            initially="DEFERRED",
            name="fk_current_tenant_id",
        ),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_staff: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # -> Relationships

    email_address: Mapped[Optional["EmailAddressORM"]] = relationship(
        back_populates=None,
    )
    phone_number: Mapped[Optional["PhoneNumberORM"]] = relationship(
        back_populates=None,
    )
    current_tenant: Mapped[Optional["TenantORM"]] = relationship(
        foreign_keys=[current_tenant_id],
        back_populates=None,
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"

    def __str__(self) -> str:
        if self.display_name.strip():
            return f"{self.display_name} ({self.username})"
        return self.username
