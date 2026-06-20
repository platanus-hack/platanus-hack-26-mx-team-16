"""``NotificationPrefs`` domain model (06-data-model §3.6). PK is ``user_id``."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationPrefs(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email_enabled: bool = True
    slack_webhook_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
