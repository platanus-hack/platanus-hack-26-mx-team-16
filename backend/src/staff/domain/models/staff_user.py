"""Modelos de dominio del módulo staff (ADR 0001 · D7).

Rol de plataforma Llamitai para la consola staff cross-tenant. El staff se
revoca (``status=revoked`` + ``revoked_at``), nunca se borra: la dependencia
``StaffUserDep`` consulta la fila activa por request, por lo que la
revocación surte efecto inmediato aunque el JWT con ``is_staff`` siga vivo.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.base_enum import BaseEnum


class StaffRole(str, BaseEnum):
    """Rol del staff: analista L1 de la cola unificada o admin de plataforma."""

    STAFF_ANALYST_L1 = "staff_analyst_l1"
    STAFF_ADMIN = "staff_admin"


class StaffUserStatus(str, BaseEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class StaffUser(BaseModel):
    uuid: UUID = Field(...)
    # FK users.uuid (UNIQUE): identidad global; el staff NO es un tenant user.
    user_id: UUID = Field(...)
    role: StaffRole = Field(...)
    status: StaffUserStatus = Field(default=StaffUserStatus.ACTIVE)
    created_at: datetime | None = Field(default=None)
    revoked_at: datetime | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    @property
    def is_active(self) -> bool:
        return self.status is StaffUserStatus.ACTIVE

    @property
    def persist_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "role": self.role.value,
            "status": self.status.value,
            "revoked_at": self.revoked_at,
        }
