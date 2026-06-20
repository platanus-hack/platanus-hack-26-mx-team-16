"""``PublicReport`` domain model (06-data-model §3.7)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PublicReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    token: str
    scan_id: UUID
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def is_servable(self, *, now: datetime | None = None) -> bool:
        """True unless revoked or expired (the 410 itself is emitted by 12-api)."""
        moment = now or datetime.now(timezone.utc)
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at < moment:
            return False
        return True
