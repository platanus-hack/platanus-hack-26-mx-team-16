from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDTimestampMixin


class ProcessRecordORM(Base, UUIDTimestampMixin):
    __tablename__ = "process_records"
    __table_args__ = (
        Index("ix_process_records_tenant_processed_at", "tenant_id", "processed_at"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("tenants.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    object_key_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    analysis_run_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_analysis_runs.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<ProcessRecord tenant={self.tenant_id} pages={self.page_count} at={self.processed_at}>"
