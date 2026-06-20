from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class WorkflowEventORM(Base, UUIDTenantTimestampMixin):
    """Append-only outbound webhook events (spec standard-webhooks §4.1)."""

    __tablename__ = "workflow_events"
    __table_args__ = (
        # Idempotency per run (§4.1/§5.14): a retry of the same activity reuses
        # the row; a re-extraction (new run_id) creates a new event. The same
        # (document, type, run) fans out to one row PER destination, so the
        # destination is part of the idempotency key.
        UniqueConstraint("event_id", name="uq_workflow_events_event_id"),
        UniqueConstraint(
            "document_id",
            "event_type",
            "idempotency_key",
            "destination_id",
            name="uq_workflow_events_doc_type_job",
        ),
        # Used by the retry job (§4.8) and the delivery-log UI (§10).
        Index("ix_workflow_events_delivery_status", "delivery_status"),
        Index("ix_workflow_events_tenant_workflow_created", "tenant_id", "workflow_id", "created_at"),
        Index("ix_workflow_events_destination_created", "destination_id", "created_at"),
    )

    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)

    workflow_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    processing_job_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_processing_jobs.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    document_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_documents.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    # The destination this delivery targets. Nullable for legacy rows created
    # before multi-destination support (spec connections §4.3). FK points at the
    # generalised ``workflow_destinations`` table (decision D4).
    destination_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_destinations.uuid", ondelete="SET NULL"),
        nullable=True,
    )

    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    document_status: Mapped[str] = mapped_column(String(25), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    delivery_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="PENDING",
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<WorkflowEventORM(event_id={self.event_id}, "
            f"event_type={self.event_type}, delivery_status={self.delivery_status})>"
        )
