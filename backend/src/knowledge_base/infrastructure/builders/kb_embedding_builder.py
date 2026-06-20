from src.common.database.models.knowledge_base.kb_embedding import KBEmbeddingORM
from src.common.domain.models.knowledge_base.kb_embedding import KBEmbedding


def build_kb_embedding(orm_instance: KBEmbeddingORM) -> KBEmbedding:
    return KBEmbedding(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        kb_document_id=orm_instance.kb_document_id,
        chunk_index=orm_instance.chunk_index,
        chunk_text=orm_instance.chunk_text,
        embedding=list(orm_instance.embedding) if orm_instance.embedding is not None else None,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
