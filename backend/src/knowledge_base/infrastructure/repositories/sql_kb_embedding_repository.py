"""SQLAlchemy + pgvector implementation of KBEmbeddingRepository."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.knowledge_base.kb_embedding import KBEmbeddingORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.common.domain.models.knowledge_base.kb_embedding import KBEmbedding
from src.knowledge_base.domain.repositories.kb_embedding_repository import KBEmbeddingRepository
from src.knowledge_base.infrastructure.builders.kb_embedding_builder import build_kb_embedding


class SQLKBEmbeddingRepository(KBEmbeddingRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_many(self, embeddings: list[KBEmbedding]) -> list[KBEmbedding]:
        async with atomic_transaction(self.session):
            orm_instances = []
            for emb in embeddings:
                orm_instance = KBEmbeddingORM(
                    uuid=emb.uuid,
                    tenant_id=emb.tenant_id,
                    kb_document_id=emb.kb_document_id,
                    chunk_index=emb.chunk_index,
                    chunk_text=emb.chunk_text,
                    embedding=emb.embedding,
                )
                self.session.add(orm_instance)
                orm_instances.append(orm_instance)
            await self.session.flush()
            for orm_instance in orm_instances:
                await self.session.refresh(orm_instance)
        return [build_kb_embedding(orm) for orm in orm_instances]

    async def delete_by_document(self, kb_document_id: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            stmt = delete(KBEmbeddingORM).where(
                KBEmbeddingORM.kb_document_id == kb_document_id,
                KBEmbeddingORM.tenant_id == tenant_id,
            )
            await self.session.execute(stmt)
            await self.session.flush()

    async def search_similar(
        self,
        query_embedding: list[float],
        tenant_id: UUID,
        top_k: int = 5,
        kb_document_ids: list[UUID] | None = None,
    ) -> list[KBEmbedding]:
        stmt = select(KBEmbeddingORM).where(
            KBEmbeddingORM.tenant_id == tenant_id,
            KBEmbeddingORM.embedding.isnot(None),
        )

        if kb_document_ids:
            stmt = stmt.where(KBEmbeddingORM.kb_document_id.in_(kb_document_ids))

        # Order by cosine distance (ascending = most similar first)
        stmt = stmt.order_by(KBEmbeddingORM.embedding.cosine_distance(query_embedding)).limit(top_k)

        result = await self.session.execute(stmt)
        orm_instances = list(result.scalars())
        return [build_kb_embedding(orm) for orm in orm_instances]
