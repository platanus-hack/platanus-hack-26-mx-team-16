from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class ToolDefinitionORM(Base, UUIDTenantTimestampMixin):
    """Workflow-scoped Tool entry (F5 · A3, re-scoped 2026-06). Non-secret config
    only; the secret + host allowlist live on the referenced LOOKUP
    ``ConnectionAccount`` (org-level), mirroring the Connections split."""

    __tablename__ = "tool_definitions"
    __table_args__ = (UniqueConstraint("workflow_id", "name", name="uq_tool_definitions_workflow_name"),)

    workflow_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    transport: Mapped[str] = mapped_column(String(20), nullable=False, server_default="HTTP")
    # phases-config · F5: las script tools (PYTHON/JS) NO referencian una cuenta de
    # conexión (corren en sandbox, no hacen HTTP) ⇒ nullable. Las HTTP siguen
    # exigiéndola en el endpoint (capability LOOKUP).
    connection_account_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("connection_accounts.uuid", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    input_schema: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    output_schema: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    def __repr__(self) -> str:
        return f"<ToolDefinitionORM(name={self.name}, transport={self.transport})>"
