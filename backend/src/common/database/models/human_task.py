from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class HumanTaskORM(Base, UUIDTenantTimestampMixin):
    """Unified durable pause record (F6 · HumanTask)."""

    __tablename__ = "human_tasks"
    __table_args__ = (
        UniqueConstraint("task_key", name="uq_human_tasks_task_key"),
        Index("ix_human_tasks_tenant_status", "tenant_id", "status"),
        Index("ix_human_tasks_case", "case_id"),
        # E5 · colas L1/L2: índice parcial — solo tareas con stage.
        Index(
            "ix_human_tasks_stage_status",
            "stage",
            "status",
            postgresql_where=text("stage IS NOT NULL"),
        ),
    )

    task_key: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    assignee_mode: Mapped[str] = mapped_column(String(30), nullable=False, server_default="internal_queue")
    audience: Mapped[str | None] = mapped_column(String(60), nullable=True)
    workflow_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    case_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    pipeline_run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    resolution: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # E5 · revisión multinivel: `review_l1` | `review_l2`; NULL = gate único E4.
    stage: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # E5 · claim/lock pesimista: `user:<uuid>` | `staff:<uuid>`.
    claimed_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<HumanTaskORM(task_key={self.task_key}, kind={self.kind}, status={self.status})>"
