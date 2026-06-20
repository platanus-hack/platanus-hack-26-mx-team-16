"""Fetch a single WorkflowDocument by uuid, scoped to tenant."""

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.exceptions.processing import DocumentNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.domain.repositories.workflow_document import (
    WorkflowDocumentRepository,
)


@dataclass
class WorkflowDocumentByIdGetter(UseCase):
    document_id: UUID
    tenant_id: UUID
    document_repository: WorkflowDocumentRepository

    async def execute(self) -> WorkflowDocument:
        document = await self.document_repository.find_by_id(self.document_id, self.tenant_id)
        if document is None:
            raise DocumentNotFoundError(str(self.document_id))
        return document
