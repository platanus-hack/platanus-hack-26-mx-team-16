from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class WebhookDestinationORM(Base, UUIDTenantTimestampMixin):
    """A per-workflow outbound destination (spec connections §4.3 · decision D4).

    Generalised in-place to ``workflow_destinations``: ``provider`` selects the
    transport (``WEBHOOK`` today; ``SLACK``/``DRIVE``/… via F12) and ``account_id``
    optionally binds a reusable ``ConnectionAccount`` (OAuth providers). The
    ``WEBHOOK`` path is byte-identical to before (inline ``url`` + ``secret``,
    ``account_id`` NULL — decision D2). Deliveries are recorded as ``WorkflowEvent``
    rows tagged with this destination's ``uuid`` (delivery log + charts).
    """

    __tablename__ = "workflow_destinations"
    __table_args__ = (
        Index("ix_workflow_destinations_workflow", "workflow_id"),
        Index("ix_workflow_destinations_tenant_created", "tenant_id", "created_at"),
    )

    workflow_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    # Transport selector (decision D4). WEBHOOK destinations stay inline.
    provider: Mapped[str] = mapped_column(String(30), nullable=False, server_default="WEBHOOK")
    # Optional reusable connection account for OAuth providers (NULL for WEBHOOK).
    account_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("connection_accounts.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    # Sensitive HMAC signing secret; never serialized to clients (presenter omits it).
    secret: Mapped[str | None] = mapped_column(String(512), nullable=True)
    subscribed_events: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default='["document.extracted", "document.failed"]',
    )
    api_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<WebhookDestinationORM(name={self.name}, url={self.url}, enabled={self.enabled})>"
