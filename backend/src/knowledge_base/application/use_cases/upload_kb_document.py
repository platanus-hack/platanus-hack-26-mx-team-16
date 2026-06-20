"""Create the KB document row with VECTORIZING status. Caller dispatches vectorization separately."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.common.domain.exceptions.knowledge_base import (
    KBDocumentInvalidSlugError,
    KBDocumentSlugConflictError,
)
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.knowledge_base.kb_document import SLUG_PATTERN, KBDocument
from src.common.domain.enums.knowledge_base import KBDocumentStatus
from src.common.domain.services.slugify import slugify
from src.knowledge_base.domain.repositories.kb_document_repository import KBDocumentRepository

_SLUG_RE = re.compile(SLUG_PATTERN)
_UUID_SUFFIX_LEN = 6
_SLUG_BASE_LIMIT = 100 - _UUID_SUFFIX_LEN - 1  # leave room for "-XXXXXX"


@dataclass
class KBDocumentUploader(UseCase):
    tenant_id: UUID
    file_name: str
    mime_type: str
    document_repository: KBDocumentRepository
    file_id: UUID | None = None
    workflow_id: UUID | None = None
    slug: str | None = None

    async def execute(self) -> KBDocument:
        document_uuid = uuid4()
        slug = await self._resolve_slug(document_uuid)
        now = datetime.now(UTC)
        document = KBDocument(
            uuid=document_uuid,
            tenant_id=self.tenant_id,
            file_name=self.file_name,
            slug=slug,
            mime=self.mime_type,
            file_id=self.file_id,
            workflow_id=self.workflow_id,
            extracted_text=None,
            status=KBDocumentStatus.VECTORIZING,
            chunk_count=0,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        return await self.document_repository.create(document)

    async def _resolve_slug(self, document_uuid: UUID) -> str:
        if self.slug is None:
            slug = self._derive_slug(self.file_name, document_uuid)
        else:
            slug = self.slug
            if not _SLUG_RE.match(slug):
                raise KBDocumentInvalidSlugError(slug)
        await self._assert_slug_available(slug)
        return slug

    @staticmethod
    def _derive_slug(file_name: str, document_uuid: UUID) -> str:
        base = slugify(file_name, max_length=_SLUG_BASE_LIMIT)
        suffix = document_uuid.hex[:_UUID_SUFFIX_LEN]
        return f"{base}-{suffix}"

    async def _assert_slug_available(self, slug: str) -> None:
        if self.workflow_id is not None:
            existing = await self.document_repository.find_by_slug_in_workflow(self.workflow_id, slug, self.tenant_id)
            if existing is not None:
                raise KBDocumentSlugConflictError(slug, scope="workflow")
        else:
            existing = await self.document_repository.find_by_slug_at_tenant(self.tenant_id, slug)
            if existing is not None:
                raise KBDocumentSlugConflictError(slug, scope="tenant")
