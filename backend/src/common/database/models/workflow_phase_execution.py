from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class WorkflowPhaseExecutionORM(Base, UUIDTenantTimestampMixin):
    """One row per recipe phase executed in an interpreter run (an "Ejecución").

    The single engine (``PipelineInterpreterWorkflow``) writes these through the
    ``record_phase_execution`` activity as it enters/leaves each phase. They are
    the per-phase detail of a ``workflow_processing_jobs`` row and feed the
    Step-Functions-style view (phases on the left, data each phase produced on
    the right). Keyed ``(processing_job_id, seq)`` so the recorder is idempotent
    under Temporal's at-least-once activity delivery.
    """

    __tablename__ = "workflow_phase_executions"
    __table_args__ = (
        UniqueConstraint("processing_job_id", "seq", name="uq_workflow_phase_executions_job_seq"),
        Index("ix_workflow_phase_executions_job", "processing_job_id", "seq"),
    )

    processing_job_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_processing_jobs.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    phase_id: Mapped[str] = mapped_column(String(120), nullable=False)
    phase_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="RUNNING")

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    output_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<WorkflowPhaseExecutionORM(job={self.processing_job_id}, seq={self.seq}, "
            f"kind={self.phase_kind}, status={self.status})>"
        )
