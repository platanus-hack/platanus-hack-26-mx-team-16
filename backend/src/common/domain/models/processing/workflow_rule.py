from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class WorkflowRule(BaseModel):
    """A user-authored rule (spec §3.1)."""

    uuid: UUID = Field(default_factory=uuid4)
    tenant_id: UUID = Field(...)
    workflow_id: UUID = Field(...)
    name: str = Field(..., min_length=1, max_length=255)
    # Identificador estable para @rule.<slug> (x-source); fijado al crear,
    # inmune a renames.
    slug: str | None = Field(default=None, max_length=255)
    position: int = Field(default=0)
    is_active: bool = Field(default=True)
    kind: str = Field(..., min_length=1, max_length=64)
    prompt: str = Field(..., min_length=1)
    # E5 · regla condicional (columna `when_expr`): predicado `==`/`!=` sobre
    # refs `@slug.path` del caso. None = aplica siempre; falso ⇒ SKIPPED.
    when: str | None = Field(default=None)
    config: dict[str, Any] = Field(default_factory=dict)
    scope: dict[str, Any] = Field(default_factory=lambda: {"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"})
    knowledge_refs: list[UUID] = Field(default_factory=list)
    current_compilation_id: UUID | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )
