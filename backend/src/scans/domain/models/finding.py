"""``FindingRecord`` domain model (06-data-model §3.3).

The persisted projection of the frozen ``Finding`` contract plus the DB-only
identity/lifecycle fields (``uuid``, ``scan_id``, ``site_id``, ``status``,
``dedupe_key``, ``first_seen``/``last_seen``). The pure parser output stays the
``Finding`` contract; this is what lands in the ``findings`` table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FindingRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    scan_id: UUID
    site_id: UUID

    source: str
    tool: str
    category: str
    title: str
    severity: str
    cvss: float | None = None
    confidence: str
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    affected_url: str | None = None
    endpoint: str | None = None
    param: str | None = None
    impact: str
    remediation: str
    references: list[str] = Field(default_factory=list)
    status: str

    dedupe_key: str
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
