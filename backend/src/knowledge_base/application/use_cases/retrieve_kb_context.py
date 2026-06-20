"""Search KB chunks by query embedding (cosine similarity via pgvector)."""

from dataclasses import dataclass, field
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.knowledge_base.kb_embedding import KBEmbedding
from src.knowledge_base.domain.repositories.kb_embedding_repository import KBEmbeddingRepository
from src.knowledge_base.infrastructure.services.embedder import Embedder

TOP_K_CHUNKS = 5


@dataclass
class RetrieveKBContext(UseCase):
    tenant_id: UUID
    query: str
    embedding_repository: KBEmbeddingRepository
    embedder: Embedder
    top_k: int = TOP_K_CHUNKS
    kb_document_ids: list[UUID] | None = None

    async def execute(self) -> list[KBEmbedding]:
        # 1. Convert query text to embedding
        query_embedding = await self.embedder.embed(self.query)

        # 2. Search similar chunks via pgvector cosine distance
        results = await self.embedding_repository.search_similar(
            query_embedding=query_embedding,
            tenant_id=self.tenant_id,
            top_k=self.top_k,
            kb_document_ids=self.kb_document_ids,
        )

        return results
