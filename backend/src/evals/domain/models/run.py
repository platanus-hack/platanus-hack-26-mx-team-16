"""Domain model for an eval run (F11 · A5)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvalRun(BaseModel):
    """A single evaluation pass of a pipeline version over a dataset."""

    uuid: UUID
    tenant_id: UUID
    dataset_id: UUID
    pipeline_version: int | None = None
    status: str = "PENDING"
    metrics: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")
