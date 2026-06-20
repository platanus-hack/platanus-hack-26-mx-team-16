from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.knowledge_base.domain.repositories.kb_document_repository import KBDocumentRepository
from src.knowledge_base.domain.repositories.kb_embedding_repository import KBEmbeddingRepository


@dataclass
class DeleteKBDocument(UseCase):
    document_id: UUID
    tenant_id: UUID
    document_repository: KBDocumentRepository
    embedding_repository: KBEmbeddingRepository

    async def execute(self) -> None:
        # Embeddings are cascade-deleted via FK, but we explicitly clean up
        await self.embedding_repository.delete_by_document(self.document_id, self.tenant_id)
        await self.document_repository.delete(self.document_id, self.tenant_id)
