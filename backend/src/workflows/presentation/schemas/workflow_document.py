from uuid import UUID

from pydantic import Field

from src.common.domain.entities.common.requests import CamelCaseRequest


class UploadWorkflowDocumentRequest(CamelCaseRequest):
    file_id: UUID = Field(...)
    file_name: str = Field(..., min_length=1, max_length=255)
    document_type_id: UUID | None = Field(default=None)
    case_id: UUID | None = Field(default=None)


class UpdateWorkflowDocumentRequest(CamelCaseRequest):
    file_name: str | None = Field(default=None, min_length=1, max_length=255)
    extraction: dict | None = Field(default=None)
    validation: list | None = Field(default=None)
