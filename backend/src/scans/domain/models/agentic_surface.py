"""``AgenticSurface`` domain model (06-data-model §3.4)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AgenticSurface(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    scan_id: UUID
    site_id: UUID
    type: str
    vendor: str | None = None
    location_url: str
    inferred_model: str | None = None
    detected_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
