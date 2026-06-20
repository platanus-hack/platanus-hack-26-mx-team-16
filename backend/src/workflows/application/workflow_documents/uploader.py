from dataclasses import dataclass
from uuid import UUID

from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.enums.workflows import WorkflowDocumentStatus
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.exceptions.processing import DocumentNotFoundError
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository


@dataclass
class WorkflowDocumentUploader(UseCase):
    """Associates a file_id with an existing case document."""

    document_id: UUID
    tenant_id: UUID
    file_id: UUID
    file_name: str
    document_repository: WorkflowDocumentRepository

    async def execute(self) -> WorkflowDocument:
        document = await self.document_repository.find_by_id(self.document_id, self.tenant_id)
        if not document:
            raise DocumentNotFoundError(str(self.document_id))

        document.file_id = self.file_id
        document.file_name = self.file_name
        document.status = WorkflowDocumentStatus.UPLOADED

        return await self.document_repository.update(document)
