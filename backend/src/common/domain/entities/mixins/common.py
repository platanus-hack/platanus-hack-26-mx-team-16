from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from uuid6 import uuid7


class BaseModelMixin(BaseModel):
    uuid: UUID = Field(default_factory=uuid7)

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )


class TimestampMixin(BaseModel):
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)


class TenantMetadataMixin(BaseModel):
    tenant: str | None = Field(default=None)
    tenant_id: str | None = Field(default=None)
    tenant_branch_id: str | None = Field(default=None)

    @property
    def to_dict(self) -> dict[str, Any]:
        data = dict()
        if self.tenant:
            data["tenant"] = self.tenant
        if self.tenant_id:
            data["tenant_id"] = self.tenant_id
        if self.tenant_branch_id:
            data["tenant_branch_id"] = self.tenant_branch_id
        return data
