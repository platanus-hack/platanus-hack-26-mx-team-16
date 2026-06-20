from uuid import UUID

from pydantic import Field

from src.common.domain.entities.common.requests import CamelCaseRequest


class CreateDocumentTypeRequest(CamelCaseRequest):
    name: str = Field(..., min_length=1, max_length=255)
    is_shareable: bool = Field(default=False)
    description: str | None = Field(default=None)
    fields: dict | None = Field(default=None)
    validation_rules: list[dict] | None = Field(default=None)


class UpdateDocumentTypeRequest(CamelCaseRequest):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_shareable: bool | None = Field(default=None)
    description: str | None = Field(default=None)
    fields: dict | None = Field(default=None)
    keywords: list[str] | None = Field(default=None)
    examples: list[str] | None = Field(default=None)
    validation_rules: list[dict] | None = Field(default=None)
    sample_file_id: UUID | None = Field(default=None)


class SuggestDocumentTypeFieldsRequest(CamelCaseRequest):
    prompt: str | None = Field(default=None, max_length=2000)
