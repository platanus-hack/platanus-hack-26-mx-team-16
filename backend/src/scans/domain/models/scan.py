"""``Scan`` domain model (06-data-model §3.2).

Mirrors the ``scans`` row, including the Python-computed score/observability
columns. Persisted by the worker (05-agent-team), read by scoring (07) and the
API (12). The PK is exposed as ``uuid`` (passthrough), never renamed to ``id``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Scan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    site_id: UUID
    level: str
    status: str
    visibility: str

    requested_by: UUID | None = None
    authorized: bool = False
    authorized_at: datetime | None = None

    # Observability / live-view
    progress: int = 0
    current_phase: str | None = None
    tools_status: dict[str, Any] | None = None
    coverage: list[dict[str, Any]] | None = None
    error: str | None = None

    # Scoring (Python-computed)
    web_score: int | None = None
    agentic_score: int | None = None
    overall_score: int | None = None
    overall_grade: str | None = None
    agentic_status: str | None = None
    penalty_raw: int | None = None
    summary: dict[str, Any] | None = None

    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
