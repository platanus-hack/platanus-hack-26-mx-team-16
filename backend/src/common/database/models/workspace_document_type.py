from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class WorkflowDocumentTypeORM(Base, UUIDTenantTimestampMixin):
    __tablename__ = "workflow_document_types"
    __table_args__ = (UniqueConstraint("workflow_id", "document_type_id"),)

    workflow_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.uuid", ondelete="CASCADE"),
        nullable=False,
    )

    document_type_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("document_types.uuid", ondelete="CASCADE"),
        nullable=False,
    )

    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        server_default="{}",
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<WorkflowDocumentTypeORM(workflow={self.workflow_id}, doc_type={self.document_type_id})>"
