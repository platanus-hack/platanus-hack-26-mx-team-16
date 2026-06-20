"""Evento de audit append-only del plano ``/staff/v1`` (ADR 0001 · D7).

Una fila por request staff (el middleware del router las escribe — cobertura
por construcción). ``tenant_id``/``case_id``/``task_id`` son referencias sin
FK: el audit sobrevive el borrado de tenants/casos/tareas.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StaffAccessEvent(BaseModel):
    uuid: UUID = Field(...)
    staff_user_id: UUID = Field(...)
    # Acción derivada de la ruta (p. ej. `tasks.list`, `tasks.claim`).
    action: str = Field(..., min_length=1, max_length=40)
    tenant_id: UUID | None = Field(default=None)
    case_id: UUID | None = Field(default=None)
    task_id: UUID | None = Field(default=None)
    request_id: str | None = Field(default=None, max_length=80)
    ip: str | None = Field(default=None, max_length=64)
    # Columna DB `metadata` (atributo ORM `event_metadata` — nombre reservado
    # de SQLAlchemy).
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    @property
    def persist_dict(self) -> dict[str, Any]:
        return {
            "staff_user_id": self.staff_user_id,
            "action": self.action,
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "task_id": self.task_id,
            "request_id": self.request_id,
            "ip": self.ip,
            "event_metadata": self.metadata,
        }
