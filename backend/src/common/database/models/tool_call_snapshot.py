from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class ToolCallSnapshotORM(Base, UUIDTenantTimestampMixin):
    """Append-only per-case audit snapshot of one Tool call (F5 · B1).

    B1 mandates **no reusable cache**: every case fetches live. We persist the
    request/response purely as an audit/reproducibility record, never read back as
    a cache."""

    __tablename__ = "tool_call_snapshots"
    __table_args__ = (
        Index("ix_tool_call_snapshots_case", "case_id", "created_at"),
        Index("ix_tool_call_snapshots_tool", "tool_id", "created_at"),
    )

    tool_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("tool_definitions.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    case_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    request: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ToolCallSnapshotORM(tool_id={self.tool_id}, status={self.status})>"
