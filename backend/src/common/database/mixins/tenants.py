from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import UUIDTimestampMixin


class UUIDTenantTimestampMixin(UUIDTimestampMixin):
    """Mixin for models that belong to a tenant (required)."""

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("tenants.uuid", ondelete="CASCADE"),
        nullable=False,
    )


class OptionalTenantTimestampMixin(UUIDTimestampMixin):
    tenant_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("tenants.uuid", ondelete="CASCADE"),
        nullable=True,
    )


class LocationMixin(UUIDTimestampMixin):
    address: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    state_province: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    country: Mapped[str] = mapped_column(
        String(2),  # ISO country code
        nullable=False,
    )


class OptionalLocationMixin:
    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    state_province: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    country: Mapped[str | None] = mapped_column(
        String(2),  # ISO country code
        nullable=True,
    )
    postal_code: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
    )
