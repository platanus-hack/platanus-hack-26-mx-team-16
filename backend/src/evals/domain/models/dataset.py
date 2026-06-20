"""Domain models for eval datasets and their golden cases (F11 · A5)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvalCase(BaseModel):
    """A single golden case: a pointer to an input + its expected output."""

    uuid: UUID
    tenant_id: UUID
    dataset_id: UUID
    input_ref: str
    expected: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class EvalDataset(BaseModel):
    """A tenant-scoped, named collection of golden cases for a pipeline."""

    uuid: UUID
    tenant_id: UUID
    name: str
    pipeline_slug: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")
