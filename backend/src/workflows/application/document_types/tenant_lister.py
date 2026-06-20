from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.document_type import DocumentType
from src.workflows.domain.repositories.document_type import DocumentTypeRepository


@dataclass
class DocumentTypeTenantLister(UseCase):
    tenant_id: UUID
    document_type_repository: DocumentTypeRepository

    async def execute(self) -> list[DocumentType]:
        return await self.document_type_repository.list_by_tenant(self.tenant_id)
