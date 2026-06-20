"""LLM generates rule suggestions from KB context."""

from dataclasses import dataclass, field
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.knowledge_base.kb_embedding import KBEmbedding
from src.knowledge_base.domain.repositories.kb_embedding_repository import KBEmbeddingRepository
from src.knowledge_base.infrastructure.services.embedder import Embedder

TOP_K_CHUNKS = 10


@dataclass
class SuggestRules(UseCase):
    tenant_id: UUID
    query: str
    embedding_repository: KBEmbeddingRepository
    embedder: Embedder
    top_k: int = TOP_K_CHUNKS
    kb_document_ids: list[UUID] | None = None

    async def execute(self) -> dict:
        # 1. Get relevant KB chunks
        query_embedding = await self.embedder.embed(self.query)
        chunks = await self.embedding_repository.search_similar(
            query_embedding=query_embedding,
            tenant_id=self.tenant_id,
            top_k=self.top_k,
            kb_document_ids=self.kb_document_ids,
        )

        # 2. Build context from chunks
        context_parts = [chunk.chunk_text for chunk in chunks]
        context = "\n---\n".join(context_parts)

        # 3. Return context and chunks for the caller to pass to an LLM
        # The actual LLM call is left to the presentation/orchestration layer
        return {
            "context": context,
            "chunks_used": len(chunks),
            "chunks": [
                {
                    "document_id": str(chunk.kb_document_id),
                    "chunk_index": chunk.chunk_index,
                    "chunk_text": chunk.chunk_text,
                }
                for chunk in chunks
            ],
        }
