from pydantic import Field

from src.common.domain.entities.common.requests import CamelCaseRequest


class DocumentResponse(CamelCaseRequest):
    """Schema used only for OpenAPI documentation; actual response goes through presenter."""

    uuid: str = Field(...)
    tenant_id: str = Field(...)
    file_name: str = Field(...)
    mime: str = Field(...)
    size: int = Field(...)
    s3_key: str = Field(...)
    presigned_url: str | None = Field(default=None)
    created_at: str | None = Field(default=None)
    updated_at: str | None = Field(default=None)
