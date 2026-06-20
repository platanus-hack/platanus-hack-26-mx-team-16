from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.models.knowledge_base.kb_embedding import KBEmbedding


class KBEmbeddingRepository(ABC):
    @abstractmethod
    async def create_many(self, embeddings: list[KBEmbedding]) -> list[KBEmbedding]:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_document(self, kb_document_id: UUID, tenant_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def search_similar(
        self,
        query_embedding: list[float],
        tenant_id: UUID,
        top_k: int = 5,
        kb_document_ids: list[UUID] | None = None,
    ) -> list[KBEmbedding]:
        raise NotImplementedError
