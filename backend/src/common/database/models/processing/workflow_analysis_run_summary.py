from uuid import UUID

from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class WorkflowAnalysisRunSummaryORM(Base, UUIDTenantTimestampMixin):
    __tablename__ = "workflow_analysis_run_summaries"
    __table_args__ = (
        Index(
            "uq_run_summaries_run",
            "workflow_analysis_run_id",
            unique=True,
        ),
        Index("ix_run_summaries_tenant", "tenant_id"),
    )

    workflow_analysis_run_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_analysis_runs.uuid", ondelete="CASCADE"),
        nullable=False,
    )

    # Deterministic layer
    verdict: Mapped[str] = mapped_column(String(16), nullable=False)
    signals: Mapped[list] = mapped_column(JSONB, server_default="[]", nullable=False)
    signals_by_polarity: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    signals_by_severity: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    blocking_failures: Mapped[list] = mapped_column(JSONB, server_default="[]", nullable=False)
    degraded_rules: Mapped[list] = mapped_column(JSONB, server_default="[]", nullable=False)

    # Synthesis layer
    output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # E2 · spec case-output §4.5 (migration e6f7a8b9c0d1): Citations per output
    # field, keyed by JSON Pointer.
    output_provenance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_schema_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    synthesis_template_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    narrative_status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="PENDING")
    narrative_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Reproducibility
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<WorkflowAnalysisRunSummaryORM(run={self.workflow_analysis_run_id}, "
            f"verdict={self.verdict}, narrative={self.narrative_status})>"
        )
