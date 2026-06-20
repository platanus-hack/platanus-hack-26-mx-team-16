import asyncio
from dataclasses import dataclass

from src.assets.domain.services.storage import StorageService
from src.knowledge_base.infrastructure.services.text_extractor import TextExtractor
from src.workflows.domain.services.document_text_extractor import DocumentTextExtractor


@dataclass
class LocalSampleTextExtractor(DocumentTextExtractor):
    storage_service: StorageService

    async def extract(self, s3_key: str, **kwargs) -> str:
        file_name: str = kwargs.get("file_name", "")
        mime_type: str = kwargs.get("mime_type", "")
        in_memory = self.storage_service.get_file(s3_key)
        if not in_memory.file_bytes:
            return ""
        text, _ = await asyncio.to_thread(
            TextExtractor().extract, in_memory.file_bytes, file_name, mime_type
        )
        return text
