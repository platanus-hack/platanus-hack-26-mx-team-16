"""Evento de timeline del expediente (E4 · append-only)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CaseEvent(BaseModel):
    uuid: UUID
    tenant_id: UUID
    case_id: UUID
    type: str = Field(..., min_length=1, max_length=60)
    payload: dict[str, Any] = Field(default_factory=dict)
    actor: str | None = Field(default=None, max_length=120)
    # Clave de idempotencia (retry de activities): mismo dedupe_key ⇒ una fila.
    dedupe_key: str | None = Field(default=None, max_length=160)
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")
