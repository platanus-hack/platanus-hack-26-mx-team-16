from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDPrimaryKeyModelMixin


class StaffAccessEventORM(Base, UUIDPrimaryKeyModelMixin):
    """Audit append-only del plano ``/staff/v1`` (ADR 0001 · D7).

    Sin ``updated_at`` deliberadamente: las filas nunca se mutan (patrón
    ``CaseEventORM``). ``tenant_id``/``case_id``/``task_id`` van SIN FK: el
    audit debe sobrevivir el borrado de tenants/casos/tareas. El middleware
    del router staff escribe una fila por request (cobertura por construcción).
    """

    __tablename__ = "staff_access_events"
    __table_args__ = (
        Index("ix_staff_access_events_tenant", "tenant_id"),
        Index("ix_staff_access_events_staff_user", "staff_user_id"),
        Index("ix_staff_access_events_created", "created_at"),
    )

    staff_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("staff_users.uuid"),
        nullable=False,
    )
    # Acción derivada de la ruta (p. ej. `tasks.list`, `tasks.claim`).
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    tenant_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    case_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    task_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # `metadata` es atributo reservado de SQLAlchemy ⇒ atributo Python
    # `event_metadata` mapeado a la columna `metadata`.
    event_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<StaffAccessEventORM(staff_user_id={self.staff_user_id}, action={self.action})>"
