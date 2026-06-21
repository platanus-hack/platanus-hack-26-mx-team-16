"""``POST /scans/{id}/share`` request body (12-api §"Reporte público")."""

from __future__ import annotations

from pydantic import Field

from src.common.domain.entities.common.requests import CamelCaseRequest


class ShareScanRequest(CamelCaseRequest):
    # TTL in days; default 7 (settable). Bounded to a sane range.
    ttl_days: int | None = Field(default=None, ge=1, le=365)
