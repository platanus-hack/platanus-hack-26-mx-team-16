from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.workflows.domain.repositories.document_type import DocumentTypeRepository


@dataclass
class DocumentTypeDeleter(UseCase):
    document_type_id: UUID
    tenant_id: UUID
    document_type_repository: DocumentTypeRepository

    async def execute(self) -> None:
        await self.document_type_repository.delete(self.document_type_id, self.tenant_id)
