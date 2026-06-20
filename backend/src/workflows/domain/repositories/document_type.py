from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.models.processing.document_type import (
    DocumentType,
    DocumentTypeVersion,
)


class DocumentTypeRepository(ABC):
    @abstractmethod
    async def find_by_id(self, document_type_id: UUID, tenant_id: UUID) -> DocumentType | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_ids(self, document_type_ids: list[UUID], tenant_id: UUID) -> dict[UUID, str]:
        """Batch resolve ``{id: name}`` for the given ids, tenant-scoped (spec §4.5)."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_workflow(self, workflow_id: UUID, tenant_id: UUID) -> list[DocumentType]:
        raise NotImplementedError

    @abstractmethod
    async def list_slugs_by_workflow(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        exclude_document_type_id: UUID | None = None,
    ) -> set[str]:
        raise NotImplementedError

    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID) -> list[DocumentType]:
        raise NotImplementedError

    @abstractmethod
    async def create(self, document_type: DocumentType) -> DocumentType:
        raise NotImplementedError

    @abstractmethod
    async def update(self, document_type: DocumentType) -> DocumentType:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, document_type_id: UUID, tenant_id: UUID) -> None:
        raise NotImplementedError

    # --- Immutable versions (D6' · pattern: PipelineRepository) ---------------

    @abstractmethod
    async def add_version(self, version: DocumentTypeVersion) -> DocumentTypeVersion:
        """Append an immutable snapshot ((document_type_id, version) unique)."""
        raise NotImplementedError

    @abstractmethod
    async def get_version(self, document_type_id: UUID, version: int) -> DocumentTypeVersion | None:
        """Load the sealed contract a run pinned at dispatch time."""
        raise NotImplementedError

    @abstractmethod
    async def latest_version(self, document_type_id: UUID) -> DocumentTypeVersion | None:
        raise NotImplementedError
