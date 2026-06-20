from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class KBDocumentORM(Base, UUIDTenantTimestampMixin):
    __tablename__ = "kb_documents"

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    file_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("documents.uuid", ondelete="SET NULL"),
    )
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.uuid", name="fk_kb_documents_workflow_id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(25), nullable=False, server_default="vectorizing")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_kb_documents_workflow_id", "workflow_id"),
        Index(
            "uq_kb_documents_workflow_slug",
            "workflow_id",
            "slug",
            unique=True,
            postgresql_where=text("workflow_id IS NOT NULL"),
        ),
        Index(
            "uq_kb_documents_tenant_slug_global",
            "tenant_id",
            "slug",
            unique=True,
            postgresql_where=text("workflow_id IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return f"<KBDocumentORM(uuid={self.uuid}, file_name={self.file_name})>"
