"""Domain model for ``WebhookDestination`` — a per-workflow webhook endpoint.

Multiple destinations may exist per workflow (spec connections §4.3). Each owns
its URL, HMAC signing ``secret`` (persisted but never presented) and the list of
event types it is subscribed to.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.connections import ConnectionProvider


class WebhookDestination(BaseModel):
    uuid: UUID
    tenant_id: UUID
    workflow_id: UUID
    # Transport selector (decision D4). WEBHOOK keeps the inline url+secret shape;
    # OAuth providers (Slack/Drive/…) reference a ``ConnectionAccount`` by account_id.
    provider: ConnectionProvider = ConnectionProvider.WEBHOOK
    account_id: UUID | None = None
    name: str
    url: str
    description: str | None = None
    enabled: bool = True
    # Sensitive signing secret. Persisted but NEVER presented to clients.
    secret: str | None = None
    subscribed_events: list[str] = Field(default_factory=lambda: ["document.extracted", "document.failed"])
    api_version: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")
