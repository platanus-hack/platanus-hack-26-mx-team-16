from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.exceptions.processing import DocumentNotFoundError
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository


@dataclass
class WorkflowDocumentUpdater(UseCase):
    document_id: UUID
    tenant_id: UUID
    document_repository: WorkflowDocumentRepository
    file_name: str | None = None
    extraction: dict | None = None
    validation: list | None = None

    async def execute(self) -> WorkflowDocument:
        document = await self.document_repository.find_by_id(self.document_id, self.tenant_id)
        if not document:
            raise DocumentNotFoundError(str(self.document_id))

        if self.file_name is not None:
            document.file_name = self.file_name
        if self.extraction is not None:
            document.extraction = self.extraction
        if self.validation is not None:
            document.validation = self.validation

        return await self.document_repository.update(document)
