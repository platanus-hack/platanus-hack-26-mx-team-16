from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class WorkflowCaseORM(Base, UUIDTenantTimestampMixin):
    __tablename__ = "workflow_cases"
    __table_args__ = (
        Index("ix_workflow_cases_workflow_id", "workflow_id"),
        Index("ix_workflow_cases_parent", "parent_case_id"),
        UniqueConstraint("workflow_id", "external_ref", name="uq_workflow_cases_workflow_external_ref"),
    )

    workflow_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="RECEIVING")
    last_ocr_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # E3 · M2M: id del sistema del cliente (find-or-create) + receta elegida
    # en POST /v1/cases (None ⇒ data-analysis para runs data-only).
    external_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pipeline_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("pipelines.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    # E4: versión sellada al arrancar el CASE# workflow + ready/completeness.
    pipeline_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("pipeline_versions.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    # E5 · fan-out a child cases (Caso 3): lineage padre→children. NULL en
    # casos normales; los children heredan pipeline sellado del padre.
    parent_case_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_cases.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completeness: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<WorkflowCaseORM(uuid={self.uuid}, name={self.name}, status={self.status})>"
