from abc import ABC, abstractmethod
from uuid import UUID

from src.evals.domain.models.dataset import EvalCase, EvalDataset


class EvalDatasetRepository(ABC):
    """Persistence for eval datasets + their golden cases (F11 · A5)."""

    @abstractmethod
    async def create(self, dataset: EvalDataset) -> EvalDataset:
        raise NotImplementedError

    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID) -> list[EvalDataset]:
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, dataset_id: UUID, tenant_id: UUID) -> EvalDataset | None:
        raise NotImplementedError

    @abstractmethod
    async def add_case(self, case: EvalCase) -> EvalCase:
        raise NotImplementedError

    @abstractmethod
    async def list_cases(self, dataset_id: UUID, tenant_id: UUID) -> list[EvalCase]:
        raise NotImplementedError
