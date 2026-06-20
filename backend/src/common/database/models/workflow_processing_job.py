from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class WorkflowProcessingJobORM(Base, UUIDTenantTimestampMixin):
    __tablename__ = "workflow_processing_jobs"
    __table_args__ = (Index("ix_workflow_processing_jobs_status", "status"),)

    temporal_workflow_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    trigger: Mapped[str] = mapped_column(String(20), nullable=False, server_default="USER")

    workflow_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_case_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_cases.uuid", ondelete="CASCADE"),
        nullable=True,
    )
    file_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("documents.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="PENDING",
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    current_step: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_seq: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    extracted_text: Mapped[str | None] = mapped_column(String(512), nullable=True)
    classified_pages: Mapped[str | None] = mapped_column(String(512), nullable=True)

    file: Mapped["DocumentORM"] = relationship(  # type: ignore[name-defined]
        "DocumentORM", foreign_keys=[file_id], lazy="select"
    )

    def __repr__(self) -> str:
        return f"<WorkflowProcessingJobORM(temporal_workflow_id={self.temporal_workflow_id}, status={self.status})>"
