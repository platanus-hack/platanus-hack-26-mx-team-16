"""Canonical citation type emitted by every rule kind during evaluation.

Citations point back to a specific extracted field on a specific document so
the UI can highlight the source value and the synthesis pipeline can build
an audit trail. The field is stable across kinds: the dispatcher emits a
Citation per resolved input, the LLM kinds emit one per cited field, and
the presenter just camelCases this shape onto the wire.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    document_id: UUID = Field(...)
    document_type_slug: str = Field(..., min_length=1, max_length=100)
    field_path: str = Field(..., min_length=0, max_length=500)
    value: str | None = Field(default=None)
    sub_check_id: str | None = Field(default=None)

    model_config = ConfigDict(frozen=True, extra="ignore")
