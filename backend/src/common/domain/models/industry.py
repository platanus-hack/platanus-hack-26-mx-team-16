from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Industry(BaseModel):
    uuid: UUID = Field(...)
    slug: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    icon: str | None = Field(default=None)
    description: str | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    @property
    def persist_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "name": self.name,
            "icon": self.icon,
            "description": self.description,
        }
