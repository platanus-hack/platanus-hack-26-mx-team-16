from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.knowledge_base import KBDocumentStatus


SLUG_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,99}$"


class KBDocument(BaseModel):
    uuid: UUID = Field(...)
    tenant_id: UUID = Field(...)
    file_name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=SLUG_PATTERN)
    mime: str = Field(..., min_length=1, max_length=100)
    file_id: UUID | None = Field(default=None)
    workflow_id: UUID | None = Field(default=None)
    extracted_text: str | None = Field(default=None)
    status: KBDocumentStatus = Field(default=KBDocumentStatus.VECTORIZING)
    chunk_count: int = Field(default=0)
    error_message: str | None = Field(default=None)
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
            "file_name": self.file_name,
            "slug": self.slug,
            "mime": self.mime,
            "file_id": self.file_id,
            "workflow_id": self.workflow_id,
            "extracted_text": self.extracted_text,
            "status": self.status.value,
            "chunk_count": self.chunk_count,
            "error_message": self.error_message,
        }
