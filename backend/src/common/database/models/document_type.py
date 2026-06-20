from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDTimestampMixin
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class DocumentTypeORM(Base, UUIDTenantTimestampMixin):
    __tablename__ = "document_types"

    workflow_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.uuid", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_shareable: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    slug: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    fields: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    keywords: Mapped[list] = mapped_column(
        JSONB,
        server_default="[]",
        nullable=False,
    )

    examples: Mapped[list] = mapped_column(
        JSONB,
        server_default="[]",
        nullable=False,
    )

    validation_rules: Mapped[list] = mapped_column(
        JSONB,
        server_default="[]",
        nullable=False,
    )

    sample_file_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("documents.uuid", ondelete="SET NULL"),
        nullable=True,
    )

    sample_file_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        server_default="{}",
        nullable=False,
    )

    # Puntero a la versión activa en `document_type_versions` (patrón
    # PipelineORM.current_version, D6'). `fields`/`validation_rules` de esta
    # tabla siguen siendo la verdad "current"; las versiones son el historial
    # inmutable + lo que cada run sella.
    current_version: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<DocumentTypeORM(uuid={self.uuid}, name={self.name})>"


class DocumentTypeVersionORM(Base, UUIDTimestampMixin):
    """An immutable, append-only snapshot of a document type's extraction
    contract (``fields`` JSON Schema + per-doc ``validation_rules``), in the
    mold of :class:`PipelineVersionORM` (D6' · E2). No tenant mixin — scope is
    inherited through the FK."""

    __tablename__ = "document_type_versions"
    __table_args__ = (
        UniqueConstraint(
            "document_type_id",
            "version",
            name="uq_document_type_versions_doctype_version",
        ),
    )

    document_type_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("document_types.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False)

    fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    validation_rules: Mapped[list] = mapped_column(
        JSONB,
        server_default="[]",
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<DocumentTypeVersionORM(document_type_id={self.document_type_id}, version={self.version})>"
