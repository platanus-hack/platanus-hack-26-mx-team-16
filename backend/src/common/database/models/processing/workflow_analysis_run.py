from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class WorkflowAnalysisRunORM(Base, UUIDTenantTimestampMixin):
    __tablename__ = "workflow_analysis_runs"
    __table_args__ = (
        Index("ix_workflow_analysis_runs_workflow_case_id", "workflow_case_id"),
        Index("ix_workflow_analysis_runs_workflow_case_status", "workflow_case_id", "status"),
    )

    workflow_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_case_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_cases.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="RUNNING")
    trigger: Mapped[str] = mapped_column(String(20), nullable=False, server_default="USER")
    triggered_by: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_by: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    reviewer_model: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    critic_model: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    consensus_samples: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    rules_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rules_passed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rules_failed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rules_inconclusive: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<WorkflowAnalysisRunORM(uuid={self.uuid}, status={self.status})>"
