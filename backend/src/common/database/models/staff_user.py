from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDPrimaryKeyModelMixin


class StaffUserORM(Base, UUIDPrimaryKeyModelMixin):
    """Rol de plataforma Llamitai (ADR 0001 · D7 — consola staff cross-tenant).

    Sin ``tenant_id`` deliberadamente: el staff opera cross-tenant por la
    superficie ``/staff/v1`` separada. Se revoca (``status='revoked'`` +
    ``revoked_at``), nunca se borra — los FKs sin cascade de
    ``staff_access_events`` protegen el audit trail. Sin ``updated_at``:
    el único cambio de estado legal es la revocación.
    """

    __tablename__ = "staff_users"
    __table_args__ = (UniqueConstraint("user_id", name="uq_staff_users_user_id"),)

    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.uuid"),
        nullable=False,
    )
    # `staff_analyst_l1` | `staff_admin` (StaffRole).
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    # `active` | `revoked` (StaffUserStatus). La dependencia StaffUserDep
    # consulta la fila por request ⇒ revocación inmediata.
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<StaffUserORM(uuid={self.uuid}, user_id={self.user_id}, role={self.role}, status={self.status})>"
