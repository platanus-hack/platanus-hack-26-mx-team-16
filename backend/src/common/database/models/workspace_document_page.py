from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class DocumentPageORM(Base, UUIDTenantTimestampMixin):
    __tablename__ = "document_pages"
    __table_args__ = (UniqueConstraint("document_id", "page_number"),)

    document_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("documents.uuid", ondelete="CASCADE"),
        nullable=False,
    )

    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="1-indexed page number",
    )

    page_file: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="S3 key for the page image",
    )

    cleaned_page_file: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="S3 key for the cleaned page image",
    )

    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<DocumentPageORM(document={self.document_id}, page={self.page_number})>"
