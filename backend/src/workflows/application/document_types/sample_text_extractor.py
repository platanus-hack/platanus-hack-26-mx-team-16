from dataclasses import dataclass
from uuid import UUID

from src.common.application.logging import get_logger
from src.common.domain.interfaces.use_case import UseCase
from src.storage.domain.repositories.file_repository import FileRepository
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.services.document_text_extractor import DocumentTextExtractor

logger = get_logger(__name__)


@dataclass
class ExtractDocumentTypeSampleText(UseCase):
    document_type_id: UUID
    tenant_id: UUID
    document_type_repository: DocumentTypeRepository
    file_repository: FileRepository
    text_extractor: DocumentTextExtractor

    async def execute(self) -> None:
        doctype = await self.document_type_repository.find_by_id(self.document_type_id, self.tenant_id)
        if doctype is None or doctype.sample_file_id is None:
            return

        document = await self.file_repository.find_by_id(doctype.sample_file_id, self.tenant_id)
        if document is None:
            logger.warning(
                "sample_text_extractor.file_not_found",
                doctype_id=self.document_type_id,
                file_id=doctype.sample_file_id,
            )
            return

        text = await self.text_extractor.extract(
            s3_key=document.s3_key,
            file_name=document.file_name,
            mime_type=document.mime,
        )
        if text:
            doctype.sample_file_text = text
            await self.document_type_repository.update(doctype)
        else:
            logger.warning("sample_text_extractor.empty_text", doctype_id=self.document_type_id)
