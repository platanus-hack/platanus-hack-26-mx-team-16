from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.knowledge_base.kb_document import KBDocument
from src.knowledge_base.domain.repositories.kb_document_repository import KBDocumentRepository


@dataclass
class ListKBDocuments(UseCase):
    tenant_id: UUID
    document_repository: KBDocumentRepository
    workflow_id: UUID | None = None

    async def execute(self) -> list[KBDocument]:
        if self.workflow_id is not None:
            return await self.document_repository.list_by_workflow(self.workflow_id, self.tenant_id)
        return await self.document_repository.list_by_tenant(self.tenant_id)
