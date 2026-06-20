from dataclasses import dataclass
from uuid import UUID

from src.common.domain.exceptions.processing import (
    DocumentTypeNotFoundError,
    SampleDocumentNotFoundError,
    SampleTextNotExtractedError,
)
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.document_type import (
    DocumentType,
    DocumentTypeVersion,
)
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.services.field_suggester import FieldSuggester


@dataclass
class SuggestDocumentTypeFields(UseCase):
    document_type_id: UUID
    tenant_id: UUID
    document_type_repository: DocumentTypeRepository
    field_suggester: FieldSuggester
    prompt: str | None = None

    async def execute(self) -> DocumentType:
        doctype = await self.document_type_repository.find_by_id(self.document_type_id, self.tenant_id)
        if not doctype:
            raise DocumentTypeNotFoundError(str(self.document_type_id))
        if not doctype.sample_file_id:
            raise SampleDocumentNotFoundError(str(self.document_type_id))
        if not doctype.sample_file_text:
            raise SampleTextNotExtractedError(str(self.document_type_id))

        schema = await self.field_suggester.suggest(
            extracted_text=doctype.sample_file_text,
            doctype_name=doctype.name,
            prompt=self.prompt,
        )
        doctype.fields = schema

        # Cambio de contrato de extracción ⇒ versión inmutable nueva (D6'),
        # igual que en DocumentTypeUpdater. Sin esto, `current_version`
        # apuntaría a un snapshot distinto de los `fields` vigentes y el
        # sellado por run mentiría.
        new_version = (doctype.current_version or 0) + 1
        await self.document_type_repository.add_version(
            DocumentTypeVersion(
                document_type_id=doctype.uuid,
                version=new_version,
                fields=doctype.fields,
                validation_rules=doctype.validation_rules,
            )
        )
        doctype.current_version = new_version
        return await self.document_type_repository.update(doctype)
