from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.exceptions.processing import DocumentNotFoundError
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository
from src.common.domain.exceptions.storage import FileNotFoundError
from src.storage.domain.repositories.file_repository import FileRepository
from src.workflows.domain.document import Document


@dataclass
class DocumentGetter(UseCase):
    document_id: UUID
    tenant_id: UUID
    document_repository: WorkflowDocumentRepository
    file_repository: FileRepository

    async def execute(self) -> Document:
        workflow_document = await self.document_repository.find_by_id(
            document_id=self.document_id,
            tenant_id=self.tenant_id,
        )

        if workflow_document is None:
            raise DocumentNotFoundError(str(self.document_id))

        if workflow_document.file_id is None:
            raise DocumentNotFoundError(f"Document {self.document_id} has no file attached")

        file_document = await self.file_repository.find_by_id(
            file_id=workflow_document.file_id,
            tenant_id=self.tenant_id,
        )
        if file_document is None:
            raise FileNotFoundError(str(workflow_document.file_id))

        return Document(
            document_id=self.document_id,
            object_key=file_document.s3_key,
        )
