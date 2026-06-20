from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class WorkflowORM(Base, UUIDTenantTimestampMixin):
    __tablename__ = "workflows"
    __table_args__ = (Index("ix_workflows_tenant_archived_created", "tenant_id", "is_archived", "created_at"),)

    created_by_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="SET NULL"),
        nullable=True,
    )

    industry_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("industries.uuid", ondelete="SET NULL"),
        nullable=True,
    )

    # Receta que corre todo upload de este workflow (E1: un solo motor).
    # NULL ⇒ el dispatcher cae al pipeline `standard-extraction` del tenant.
    pipeline_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("pipelines.uuid", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # E7 · F2: `workflow_type` retirado (migración drop column). Las capacidades
    # se derivan del pipeline; la columna ya no existe.

    # --- Access control (workflow permissions) ----------------------------------
    # "organization" (every tenant member) or "private" (only explicit members).
    access_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="organization",
    )

    # --- Fields absorbed from ProcessORM ---
    slug: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    icon: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    generic_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    extraction_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    prompt_overrides: Mapped[dict] = mapped_column(
        JSONB,
        server_default="{}",
        nullable=False,
    )

    # --- Fields absorbed from WorkflowORM (formerly ExtractionWorkflowORM) ---
    selected_doc_types: Mapped[list] = mapped_column(
        JSONB,
        server_default="[]",
        nullable=False,
    )

    kb_document_ids: Mapped[list] = mapped_column(
        JSONB,
        server_default="[]",
        nullable=False,
    )

    per_doc_kb_ids: Mapped[dict] = mapped_column(
        JSONB,
        server_default="{}",
        nullable=False,
    )

    structuring_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    llm_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # --- Analysis pipeline configuration (defaults applied in code, not DB) ---
    analysis_reviewer_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    analysis_critic_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    analysis_consensus_samples: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # --- Synthesis configuration (workflow-analysis-run summary) ---
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    synthesis_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    synthesis_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    # F4/A4: feed case documents (mapped_extraction) into synthesis + the input
    # hash. Off ⇒ lean output from verdicts only (farmacia); on ⇒ circulares.
    synthesis_uses_documents: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    # --- Outbound webhooks configuration (spec standard-webhooks §4.9) ---
    webhook_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    webhook_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    webhook_events: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default='["document.extracted", "document.failed"]',
    )
    # Sustantivo visible del caso por workflow (es/en · one/other). null ⇒ la UI
    # usa el default i18n («Caso/Casos», "Case/Cases"). `case` es el término
    # técnico estable (product/specs/data-model/case-noun.md).
    case_noun: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # --- Original WorkspaceORM fields ---
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        server_default="{}",
        nullable=False,
    )

    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    is_main: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    def __repr__(self) -> str:
        return f"<WorkflowORM(uuid={self.uuid}, name={self.name})>"
