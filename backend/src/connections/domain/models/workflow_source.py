"""Domain model for ``WorkflowSource`` — a configurable ingest origin (F8 · D1·D5·D7).

Every file ingest is a Source (W2). ``WEBHOOK`` is active (the HTTP upload IS the
source webhook); ``DRIVE``/``EMAIL``/``WHATSAPP`` are modelled for F12. The
``route_token`` is a dedicated unique column (D7) resolved by
``POST /v1/ingest/{token}``; the ``secret`` authenticates the call per
``auth_mode`` (D3). Lives in the ``connections`` module next to accounts (D5).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.connections import ConnectionProvider
from src.common.domain.enums.sources import SourceAuthMode


class WorkflowSource(BaseModel):
    uuid: UUID
    tenant_id: UUID
    workflow_id: UUID
    provider: ConnectionProvider = ConnectionProvider.WEBHOOK
    account_id: UUID | None = None  # NULL for WEBHOOK (inline); set for OAuth providers
    route_token: str  # dedicated unique routing identity (src_…)
    auth_mode: SourceAuthMode = SourceAuthMode.API_KEY
    # api_key mode: hash of the dxk_ key; hmac mode: the whsec_ signing secret.
    secret: str | None = None
    config: dict = Field(default_factory=dict)
    enabled: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")
