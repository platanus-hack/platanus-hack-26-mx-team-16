"""List WorkflowDocuments belonging to a case (scoped to tenant)."""

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.domain.repositories.workflow_document import (
    WorkflowDocumentRepository,
)


@dataclass
class WorkflowDocumentLister(UseCase):
    case_id: UUID
    tenant_id: UUID
    document_repository: WorkflowDocumentRepository

    async def execute(self) -> list[WorkflowDocument]:
        return await self.document_repository.list_by_case(self.case_id, self.tenant_id)
