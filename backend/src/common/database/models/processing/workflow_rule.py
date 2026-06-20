from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class WorkflowRuleORM(Base, UUIDTenantTimestampMixin):
    __tablename__ = "workflow_rules"
    __table_args__ = (
        Index("ix_workflow_rules_workflow", "workflow_id"),
        Index("ix_workflow_rules_tenant", "tenant_id"),
        UniqueConstraint("workflow_id", "slug", name="uq_workflow_rules_workflow_slug"),
    )

    workflow_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Identificador estable para @rule.<slug> en x-source (spec case-output).
    # Se fija al crear; renombrar la regla NO lo regenera.
    slug: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # E5 · regla condicional: predicado `when` del dominio (`==`/`!=` sobre
    # refs `@slug.path` del caso). NULL = la regla aplica siempre. Si el
    # predicado evalúa falso ⇒ resultado SKIPPED (no afecta verdict).
    when_expr: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    scope: Mapped[dict] = mapped_column(
        JSONB,
        server_default='{"mode":"ALL_DOCUMENTS","on_empty":"SKIPPED"}',
        nullable=False,
    )
    knowledge_refs: Mapped[list[UUID]] = mapped_column(
        ARRAY(PostgreSQLUUID(as_uuid=True)),
        server_default="{}",
        nullable=False,
    )
    current_compilation_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "workflow_rule_compilations.uuid",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_workflow_rules_current_compilation",
        ),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<WorkflowRuleORM(uuid={self.uuid}, kind={self.kind}, name={self.name})>"
