"""``Alert`` domain model (06-data-model §3.6)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Alert(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    user_id: UUID
    site_id: UUID
    scan_id: UUID | None = None
    type: str
    message: str
    channel: str
    sent_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
