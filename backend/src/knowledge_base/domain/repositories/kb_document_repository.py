from abc import ABC, abstractmethod
from collections.abc import Iterable
from uuid import UUID

from src.common.domain.models.knowledge_base.kb_document import KBDocument


class KBDocumentRepository(ABC):
    @abstractmethod
    async def find_by_id(self, document_id: UUID, tenant_id: UUID) -> KBDocument | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID) -> list[KBDocument]:
        raise NotImplementedError

    @abstractmethod
    async def list_by_workflow(self, workflow_id: UUID, tenant_id: UUID) -> list[KBDocument]:
        raise NotImplementedError

    @abstractmethod
    async def create(self, document: KBDocument) -> KBDocument:
        raise NotImplementedError

    @abstractmethod
    async def update(self, document: KBDocument) -> KBDocument:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, document_id: UUID, tenant_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_slug_in_workflow(self, workflow_id: UUID, slug: str, tenant_id: UUID) -> KBDocument | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_slug_at_tenant(self, tenant_id: UUID, slug: str) -> KBDocument | None:
        raise NotImplementedError

    @abstractmethod
    async def resolve_slugs(self, tenant_id: UUID, workflow_id: UUID, slugs: Iterable[str]) -> dict[str, KBDocument]:
        raise NotImplementedError
