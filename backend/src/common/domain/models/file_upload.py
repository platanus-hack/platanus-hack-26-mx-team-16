from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Document(BaseModel):
    uuid: UUID = Field(...)
    tenant_id: UUID = Field(...)
    file_name: str = Field(..., min_length=1, max_length=255)
    mime: str = Field(..., min_length=1, max_length=100)
    size: int = Field(...)
    s3_key: str = Field(..., min_length=1, max_length=512)
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
            "mime": self.mime,
            "size": self.size,
            "s3_key": self.s3_key,
        }
