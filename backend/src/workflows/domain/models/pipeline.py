"""Domain models for the configurable pipeline engine (F1 · decision A1; ADR 0002).

``Pipeline`` is the logical container **owned 1:1 by a workflow** (``workflow_id``
FK NOT NULL + UNIQUE — ADR 0002); ``PipelineVersion`` holds the immutable,
append-only recipe (an ordered list of :class:`PhaseSpec`). A run seals
``pipeline_id`` + ``version`` at start time, so editing a pipeline (= a new
version) never mutates an in-flight run — the determinism contract Temporal needs.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.pipelines import PhaseKind, PipelineKind, PipelineStatus


class PhaseSpec(BaseModel):
    """A single phase as data. ``kind`` selects the handler; ``config`` tunes it."""

    id: str
    kind: PhaseKind
    config: dict = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class PipelineVersion(BaseModel):
    """An immutable recipe snapshot. ``version`` is unique per pipeline."""

    uuid: UUID
    pipeline_id: UUID
    version: int
    phases: list[PhaseSpec] = Field(default_factory=list)
    # JSON-schema of the pipeline's final output; drives the webhook payload (W1)
    # and the default ``subscribed_events`` (D8). Optional for pure extraction.
    output_schema: dict | None = None
    # D-A: completitud + activación viven plegadas en config de fase
    # (await_documents.config / extraction_gate.config.activation), no a nivel-versión.
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class Pipeline(BaseModel):
    uuid: UUID
    # ADR 0002: the workflow that *owns* this pipeline (1:1, FK NOT NULL + UNIQUE).
    # Editing a pipeline can never affect another workflow — there are no shared
    # pipelines. Reuse happens via "Duplicate workflow" (deep-copy), not reference.
    workflow_id: UUID
    # Denormalised for authz/query scoping (the owning workflow already pins it).
    tenant_id: UUID
    # Informative only (display + export/import); unique *per workflow*, not per tenant.
    slug: str
    name: str
    kind: PipelineKind
    status: PipelineStatus = PipelineStatus.ACTIVE
    # The version a new run seals onto. ``None`` until the first version is loaded.
    current_version: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")
