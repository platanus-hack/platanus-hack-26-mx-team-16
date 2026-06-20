from abc import ABC, abstractmethod
from uuid import UUID

from src.evals.domain.models.run import EvalRun


class EvalRunRepository(ABC):
    """Persistence for eval runs (F11 · A5)."""

    @abstractmethod
    async def create(self, run: EvalRun) -> EvalRun:
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, run_id: UUID, tenant_id: UUID) -> EvalRun | None:
        raise NotImplementedError
