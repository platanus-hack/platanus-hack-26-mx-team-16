from dataclasses import dataclass
from uuid import UUID

from src.common.domain.exceptions.processing import DocumentTypeNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.document_type import DocumentType
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.services.document_type_slug import (
    compute_unique_slug,
    slugify_doctype_name,
)


@dataclass
class DocumentTypeGetter(UseCase):
    document_type_id: UUID
    tenant_id: UUID
    document_type_repository: DocumentTypeRepository

    async def execute(self) -> DocumentType:
        document_type = await self.document_type_repository.find_by_id(self.document_type_id, self.tenant_id)
        if not document_type:
            raise DocumentTypeNotFoundError(str(self.document_type_id))

        # Backfill: legacy doctypes were created before slugs were enforced.
        # Persist a freshly-derived slug so downstream consumers can rely on it.
        if document_type.slug is None:
            existing = await self.document_type_repository.list_slugs_by_workflow(
                document_type.workflow_id,
                self.tenant_id,
                exclude_document_type_id=document_type.uuid,
            )
            document_type.slug = compute_unique_slug(slugify_doctype_name(document_type.name), existing)
            document_type = await self.document_type_repository.update(document_type)

        return document_type
