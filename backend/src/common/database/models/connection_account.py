from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class ConnectionAccountORM(Base, UUIDTenantTimestampMixin):
    """Org-level connection account (spec connections §2.1)."""

    __tablename__ = "connection_accounts"
    __table_args__ = (
        Index("ix_connection_accounts_tenant_created", "tenant_id", "created_at"),
    )

    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    capabilities: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="CONNECTED")
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    # Sensitive material; never serialized to clients (presenter omits it).
    secret: Mapped[str | None] = mapped_column(String(512), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ConnectionAccountORM(provider={self.provider}, "
            f"display_name={self.display_name}, status={self.status})>"
        )
