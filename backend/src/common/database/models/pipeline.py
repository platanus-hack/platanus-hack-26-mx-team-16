from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDTimestampMixin
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class PipelineORM(Base, UUIDTenantTimestampMixin):
    """A configurable pipeline **owned 1:1 by a workflow** (F1 · A1 · ADR 0002).

    The recipe itself lives in immutable :class:`PipelineVersionORM` rows; this
    table is just the logical container + a pointer to the active version a new
    run seals onto. ``workflow_id`` is NOT NULL + UNIQUE: every workflow owns
    exactly one pipeline and no pipeline is shared.
    """

    __tablename__ = "pipelines"
    __table_args__ = (UniqueConstraint("workflow_id", name="uq_pipelines_workflow_id"),)

    workflow_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ACTIVE")
    current_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<PipelineORM(slug={self.slug}, kind={self.kind}, v={self.current_version})>"


class PipelineVersionORM(Base, UUIDTimestampMixin):
    """An immutable, append-only recipe snapshot. ``phases`` is the ordered list
    of phase-specs the interpreter walks; ``output_schema`` drives the webhook
    payload (W1) and default subscriptions (D8)."""

    __tablename__ = "pipeline_versions"
    __table_args__ = (UniqueConstraint("pipeline_id", "version", name="uq_pipeline_versions_pipeline_version"),)

    pipeline_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("pipelines.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    phases: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # D-A: completitud + activación viven plegadas en config de fase
    # (await_documents.config / extraction_gate.config.activation) — no hay columnas de policy.

    def __repr__(self) -> str:
        return f"<PipelineVersionORM(pipeline_id={self.pipeline_id}, version={self.version})>"
