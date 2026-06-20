from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class WorkflowDocumentORM(Base, UUIDTenantTimestampMixin):
    __tablename__ = "workflow_documents"
    __table_args__ = (
        Index("ix_wf_docs_workflow_status", "workflow_id", "status"),
        Index("ix_wf_docs_tenant_workflow", "tenant_id", "workflow_id"),
        # Backs the tenant-scoped dashboard aggregations (overview/processing).
        # Migration: 20260519.140000_d4e5f6a7b8c9_add_dashboard_indexes.
        Index(
            "ix_wf_docs_tenant_status_created",
            "tenant_id",
            "status",
            "created_at",
        ),
    )

    workflow_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.uuid", ondelete="CASCADE"),
        nullable=False,
    )

    workflow_case_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_cases.uuid", ondelete="SET NULL"),
        nullable=True,
    )

    document_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("documents.uuid", ondelete="SET NULL"),
        nullable=True,
    )

    document_type_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("document_types.uuid", ondelete="SET NULL"),
        nullable=True,
    )

    # Versión del contrato del doc type sellada por el run que clasificó este
    # documento (D6' · `document_type_versions.version`). NULL en docs sin
    # tipo o anteriores al versionado. La re-extracción NO la actualiza
    # (usa el contrato CURRENT — status quo deliberado).
    document_type_version: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(25),
        nullable=False,
        server_default="EMPTY",
    )

    # "SINGLE" = created by per-card drop-zone with a pre-assigned document_type_id
    # (updated in place when re-extracted).
    # "BULK"   = created by the global upload-and-extract flow; siblings may exist
    # sharing the same (case_id, document_id/file_id); re-extract terminates the
    # Temporal job and re-creates all siblings.
    # "SPLIT_CHILD" = doc repartido a un child case por el fan-out E5.
    # String(20) en DB desde la migración f7a8b9c0d1e2 (aquí estaba String(10)
    # cosmético; alineado en E5).
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="SINGLE",
    )

    # --- Extraction fields ---
    extraction: Mapped[dict] = mapped_column(
        JSONB,
        server_default="{}",
        nullable=False,
    )

    validation: Mapped[list] = mapped_column(
        JSONB,
        server_default="[]",
        nullable=False,
    )

    mapped_extraction: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    # Per-field confidence `{field: {value, confidence, source}}` (F4 · A6).
    # Persisted once (computed from bbox at mark time); the webhook payload and
    # the extraction_gate (vía evaluate_activation_gate) read it instead of recomputing.
    field_confidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)

    # Field paths flagged by the extraction_gate phase. Labels only — a non-empty
    # list never fails the run (F4); the review surface (F10) reads it.
    needs_clarification: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=None)

    # Capa-2 (fase `assess`, E3): confianza semántica LLM por campo
    # `{campo: float 0..1}`. Migración f7a8b9c0d1e2.
    extract_confidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)

    # Señales de la fase `assess` por campo flaggeado
    # `{campo: {signals: [...], explanation, candidates: [...]}}` (E3).
    signals: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)

    # E5 · verificación por campo (Inspection Bench / revisión L1-L2):
    # `{fieldPath: {value, verified_by, level, verified_at, previous_value}}`.
    # `verified_by`: `user:<uuid>` | `staff:<uuid>` | `external`;
    # `level`: 0=external, 1=L1, 2=L2.
    verification: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)

    # E5 · lineage doc→doc del fan-out: doc bulk original del que se partió
    # este SPLIT_CHILD (NULL si no proviene de un split).
    parent_document_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_documents.uuid", ondelete="SET NULL"),
        nullable=True,
    )

    extraction_pages: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer),
        nullable=True,
        default=None,
    )

    extracted_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    extraction_metadata: Mapped[dict] = mapped_column(
        JSONB,
        server_default="{}",
        nullable=False,
    )

    processing_job_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_processing_jobs.uuid", ondelete="SET NULL"),
        nullable=True,
    )

    document_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    page_range: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    processing_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Structured error written by the failure path of mark_document_status (spec §2.6).
    error: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Output del caso por documento (E2 · spec case-output): proyección x-source
    # + síntesis acotada a ESTE documento; provenance con Citations por campo.
    output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_provenance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<WorkflowDocumentORM(uuid={self.uuid}, name={self.name}, status={self.status})>"
