"""Persistencia del registry de clasificadores tenant-scoped (F3 · D-C)."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.workflows.domain.models.classifier import Classifier


class ClassifierRepository(ABC):
    @abstractmethod
    async def find_by_slug(self, slug: str, tenant_id: UUID) -> Classifier | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID) -> list[Classifier]:
        raise NotImplementedError

    @abstractmethod
    async def upsert(self, classifier: Classifier) -> Classifier:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, slug: str, tenant_id: UUID) -> None:
        raise NotImplementedError
