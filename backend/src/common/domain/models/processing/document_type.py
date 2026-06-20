from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(BaseModel):
    uuid: UUID = Field(...)
    tenant_id: UUID = Field(...)
    workflow_id: UUID = Field(...)
    name: str = Field(..., min_length=1, max_length=255)
    is_shareable: bool = Field(default=False)
    slug: str | None = Field(default=None)
    description: str | None = Field(default=None)
    fields: dict | None = Field(default=None)
    keywords: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    validation_rules: list[dict] = Field(default_factory=list)
    sample_file_id: UUID | None = Field(default=None)
    sample_file_text: str | None = Field(default=None)
    # Puntero a la versión inmutable activa (D6'). `fields` sigue siendo la
    # verdad "current"; `document_type_versions` guarda el historial sellado.
    current_version: int | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )


class DocumentTypeVersion(BaseModel):
    """Immutable snapshot of a doc type's extraction contract (D6' · E2)."""

    uuid: UUID = Field(default_factory=uuid4)
    document_type_id: UUID = Field(...)
    version: int = Field(..., ge=1)
    fields: dict | None = Field(default=None)
    validation_rules: list[dict] = Field(default_factory=list)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )
