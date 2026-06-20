from dataclasses import dataclass

from src.common.application.commands.knowledge_base import VectorizeKBDocumentCommand
from src.common.domain.buses.commands import CommandHandler
from src.knowledge_base.application.use_cases.vectorize_kb_document import KBDocumentVectorizer
from src.knowledge_base.domain.repositories.kb_document_repository import KBDocumentRepository
from src.knowledge_base.domain.repositories.kb_embedding_repository import KBEmbeddingRepository
from src.knowledge_base.infrastructure.services.embedder import Embedder
from src.knowledge_base.infrastructure.services.text_extractor import TextExtractor


@dataclass
class VectorizeKBDocumentHandler(CommandHandler[VectorizeKBDocumentCommand]):
    document_repository: KBDocumentRepository
    embedding_repository: KBEmbeddingRepository

    async def execute(self, command: VectorizeKBDocumentCommand):
        await KBDocumentVectorizer(
            document_id=command.document_id,
            tenant_id=command.tenant_id,
            file_name=command.file_name,
            mime_type=command.mime_type,
            file_content=command.file_content,
            document_repository=self.document_repository,
            embedding_repository=self.embedding_repository,
            text_extractor=TextExtractor(),
            embedder=Embedder(),
        ).execute()
