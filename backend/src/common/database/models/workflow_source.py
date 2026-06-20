from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class WorkflowSourceORM(Base, UUIDTenantTimestampMixin):
    """Configurable ingest origin (F8 · D1·D5·D7). 2-table model mirrors
    ``workflow_destinations``: provider + config jsonb + nullable account_id."""

    __tablename__ = "workflow_sources"
    __table_args__ = (
        UniqueConstraint("route_token", name="uq_workflow_sources_route_token"),
        Index("ix_workflow_sources_workflow", "workflow_id"),
        Index("ix_workflow_sources_tenant_created", "tenant_id", "created_at"),
    )

    workflow_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False, server_default="WEBHOOK")
    account_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("connection_accounts.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    # Dedicated unique routing identity (decision D7), NOT inside config jsonb.
    route_token: Mapped[str] = mapped_column(String(120), nullable=False)
    auth_mode: Mapped[str] = mapped_column(String(20), nullable=False, server_default="api_key")
    secret: Mapped[str | None] = mapped_column(String(512), nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    def __repr__(self) -> str:
        return f"<WorkflowSourceORM(provider={self.provider}, route_token={self.route_token})>"
