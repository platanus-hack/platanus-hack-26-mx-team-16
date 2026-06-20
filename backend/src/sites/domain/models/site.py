"""``Site`` domain model (06-data-model §3.1)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Site(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    url: str
    hostname: str
    is_gov: bool
    country: str | None = None
    owner_user_id: UUID | None = None
    latest_scan_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
