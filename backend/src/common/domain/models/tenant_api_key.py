"""Domain model for ``TenantApiKey`` — tenant-scoped M2M credential (F9 · M4).

Today only a single global ``ADMIN_API_KEY`` exists; this adds per-tenant keys so
the M2M endpoints (`POST /v1/case`, ingest, HumanTask callbacks) resolve to a
``tenant_id``. The cleartext ``dxk_`` key is shown once at mint time; only its
hash is stored and compared (reuses F0 ``hash_token``/``verify_token``).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TenantApiKey(BaseModel):
    uuid: UUID
    tenant_id: UUID
    name: str
    # Short non-secret prefix shown in the UI to identify a key (e.g. "dxk_a1b2").
    prefix: str
    key_hash: str
    enabled: bool = True
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")
