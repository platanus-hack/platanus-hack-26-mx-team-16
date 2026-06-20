from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class WorkflowRuleResultORM(Base, UUIDTenantTimestampMixin):
    __tablename__ = "workflow_rule_results"
    __table_args__ = (
        UniqueConstraint(
            "workflow_analysis_run_id",
            "rule_id",
            "document_refs_hash",
            name="uq_workflow_rule_results_run_rule_refs",
        ),
        Index("ix_workflow_rule_results_run", "workflow_analysis_run_id"),
        Index("ix_workflow_rule_results_rule", "rule_id"),
    )

    workflow_analysis_run_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_analysis_runs.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    rule_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_rules.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    case_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations: Mapped[list] = mapped_column(JSONB, server_default="[]", nullable=False)
    document_refs: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    document_refs_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    rendered_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_metadata: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<WorkflowRuleResultORM(uuid={self.uuid}, rule_id={self.rule_id}, status={self.status})>"
