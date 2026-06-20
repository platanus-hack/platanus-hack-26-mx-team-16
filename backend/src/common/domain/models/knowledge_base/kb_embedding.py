from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KBEmbedding(BaseModel):
    uuid: UUID = Field(...)
    tenant_id: UUID = Field(...)
    kb_document_id: UUID = Field(...)
    chunk_index: int = Field(...)
    chunk_text: str = Field(...)
    embedding: list[float] | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    @property
    def persist_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "kb_document_id": self.kb_document_id,
            "chunk_index": self.chunk_index,
            "chunk_text": self.chunk_text,
            "embedding": self.embedding,
        }
