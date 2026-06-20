"""Domain model for ``ConnectionAccount`` — an org-level connected account.

A reusable account (email mailbox, Slack workspace, webhook endpoint, …) that
workflows reference as an Origin and/or Destination (spec connections §2.1).
Credentials live here once at the organization level; never exposed to clients.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.connections import (
    ConnectionCapability,
    ConnectionProvider,
    ConnectionStatus,
)


class ConnectionAccount(BaseModel):
    uuid: UUID
    tenant_id: UUID
    provider: ConnectionProvider
    display_name: str
    capabilities: list[ConnectionCapability] = Field(default_factory=list)
    status: ConnectionStatus = ConnectionStatus.CONNECTED
    # Non-sensitive metadata (webhook url, slack channel, from-address, scopes…).
    config: dict = Field(default_factory=dict)
    # Sensitive material (signing secret / token). Persisted but NEVER presented.
    secret: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")
