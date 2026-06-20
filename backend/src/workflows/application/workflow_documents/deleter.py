"""Delete a WorkflowDocument by id, scoped to tenant."""

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.workflows.domain.repositories.workflow_document import (
    WorkflowDocumentRepository,
)


@dataclass
class WorkflowDocumentDeleter(UseCase):
    document_id: UUID
    tenant_id: UUID
    document_repository: WorkflowDocumentRepository

    async def execute(self) -> None:
        await self.document_repository.delete(self.document_id, self.tenant_id)
