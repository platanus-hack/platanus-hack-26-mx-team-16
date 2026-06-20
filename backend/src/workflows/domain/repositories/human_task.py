from abc import ABC, abstractmethod
from uuid import UUID

from src.workflows.domain.models.human_task import HumanTask


class HumanTaskRepository(ABC):
    """Persistence for unified durable pauses (F6)."""

    @abstractmethod
    async def upsert(self, task: HumanTask) -> HumanTask:
        """Create-or-return by ``task_key`` (idempotent across workflow replays)."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, task_id: UUID, tenant_id: UUID) -> HumanTask | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_key(self, task_key: str) -> HumanTask | None:
        raise NotImplementedError

    @abstractmethod
    async def resolve(self, task_id: UUID, tenant_id: UUID, resolution: dict) -> HumanTask | None:
        raise NotImplementedError

    @abstractmethod
    async def list_open(self, tenant_id: UUID, audience: str | None = None) -> list[HumanTask]:
        raise NotImplementedError

    @abstractmethod
    async def list_open_by_case(self, case_id: UUID, tenant_id: UUID) -> list[HumanTask]:
        """Tareas PENDING del caso (E5: lock + señal corrections por campo)."""
        raise NotImplementedError

    @abstractmethod
    async def claim(self, task_id: UUID, tenant_id: UUID, actor: str) -> HumanTask | None:
        """Claim pesimista (E5 §3.2): UPDATE condicional — solo si está PENDING
        y sin claim ajeno. ``None`` ⇒ no aplicó (el caller decide 404/409)."""
        raise NotImplementedError

    @abstractmethod
    async def release(
        self, task_id: UUID, tenant_id: UUID, actor: str, force: bool = False
    ) -> HumanTask | None:
        """Unclaim: solo el holder (o ``force=True`` para admin)."""
        raise NotImplementedError
