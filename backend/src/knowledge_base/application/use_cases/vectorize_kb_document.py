"""Vectorize a pending KB document: extract text, chunk, embed, and update status."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.knowledge_base.kb_document import KBDocument
from src.common.domain.enums.knowledge_base import KBDocumentStatus
from src.common.domain.models.knowledge_base.kb_embedding import KBEmbedding
from src.knowledge_base.domain.repositories.kb_document_repository import KBDocumentRepository
from src.knowledge_base.domain.repositories.kb_embedding_repository import KBEmbeddingRepository
from src.knowledge_base.infrastructure.services.embedder import Embedder
from src.knowledge_base.infrastructure.services.text_extractor import TextExtractor

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1_500
CHUNK_OVERLAP = 200


def _chunk_text(text: str) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


@dataclass
class KBDocumentVectorizer(UseCase):
    document_id: UUID
    tenant_id: UUID
    file_name: str
    mime_type: str
    file_content: bytes
    document_repository: KBDocumentRepository
    embedding_repository: KBEmbeddingRepository
    text_extractor: TextExtractor
    embedder: Embedder

    async def execute(self) -> KBDocument:
        document = await self.document_repository.find_by_id(self.document_id, self.tenant_id)
        if document is None:
            raise RuntimeError(f"KB document {self.document_id} not found for vectorization")

        try:
            full_text, pre_chunks = self.text_extractor.extract(
                file_content=self.file_content,
                file_name=self.file_name,
                mime_type=self.mime_type,
            )
            chunks = pre_chunks if pre_chunks is not None else _chunk_text(full_text)

            if chunks:
                embeddings_vectors = await self.embedder.embed_many(chunks)
                now = datetime.now(UTC)
                kb_embeddings = [
                    KBEmbedding(
                        uuid=uuid4(),
                        tenant_id=self.tenant_id,
                        kb_document_id=document.uuid,
                        chunk_index=idx,
                        chunk_text=chunk_text,
                        embedding=embedding_vector,
                        created_at=now,
                        updated_at=now,
                    )
                    for idx, (chunk_text, embedding_vector) in enumerate(zip(chunks, embeddings_vectors))
                ]
                await self.embedding_repository.create_many(kb_embeddings)

            document.extracted_text = full_text
            document.chunk_count = len(chunks)
            document.status = KBDocumentStatus.READY
            document.error_message = None
            return await self.document_repository.update(document)
        except Exception as exc:
            logger.exception("KB vectorization failed for document %s", self.document_id)
            document.status = KBDocumentStatus.FAILED
            document.error_message = str(exc)[:500]
            return await self.document_repository.update(document)
