from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.models.processing.document_type import DocumentType
from src.common.domain.models.processing.workflow_document import WorkflowDocument


class WorkflowDocumentGroup(BaseModel):
    document_type: DocumentType = Field(...)
    documents: list[WorkflowDocument] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )
