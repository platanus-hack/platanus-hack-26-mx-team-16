from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDPrimaryKeyModelMixin


class CaseEventORM(Base, UUIDPrimaryKeyModelMixin):
    """Timeline append-only del expediente (E4 · diseño §6.3).

    Sin ``updated_at`` deliberadamente: las filas nunca se mutan. El outbox de
    webhooks sigue siendo ``workflow_events`` — esta tabla es la bitácora del
    caso (``status.changed``, ``ready``, ``review.approved``…).
    """

    __tablename__ = "case_events"
    __table_args__ = (
        Index("ix_case_events_tenant", "tenant_id"),
        Index("ix_case_events_case_created", "case_id", "created_at"),
        # E6 · métricas QA: count_by_type_since(tenant_id?, types, since).
        Index("ix_case_events_tenant_type_created", "tenant_id", "type", "created_at"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("tenants.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    case_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflow_cases.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    actor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Idempotencia ante retries de la activity append_case_event: NULL = sin
    # dedupe (eventos repetibles); único cuando está presente.
    dedupe_key: Mapped[str | None] = mapped_column(String(160), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<CaseEventORM(case_id={self.case_id}, type={self.type})>"
