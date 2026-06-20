from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDPrimaryKeyModelMixin


class SourceDeliveryORM(Base, UUIDPrimaryKeyModelMixin):
    """Dedup ledger for inbound channel messages (E6 · diseño §5.9).

    Delivery-first: a row is inserted (``insert_if_absent``) BEFORE any side
    effect. ``UNIQUE(source_id, idempotency_key)`` makes a redelivered message
    (same Message-ID / wamid / fallback hash) a no-op. ``status`` tracks the
    lifecycle (received → processed | failed); ``case_id`` links the resolved
    case once one is created. No ``updated_at``: ``mark_status`` patches the
    single row in place but the table is conceptually a per-message ledger.
    """

    __tablename__ = "source_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "source_id", "idempotency_key", name="uq_source_deliveries_source_key"
        ),
        Index("ix_source_deliveries_source", "source_id"),
    )

    source_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_sources.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="received")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    case_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<SourceDeliveryORM(source_id={self.source_id}, "
            f"idempotency_key={self.idempotency_key}, status={self.status})>"
        )
