from abc import ABC, abstractmethod
from uuid import UUID

from src.staff.domain.entities import StaffQueueItem
from src.workflows.domain.models.human_task import HumanTask


class StaffHumanTaskRepository(ABC):
    """Lectura/claim cross-tenant ACOTADA de la cola L1 (ADR 0001).

    Sin ``tenant_id`` en las firmas — el tenant sale de la fila — pero TODA
    query fija ``stage='review_l1'`` y ``assignee_mode='internal_queue'``:
    el staff jamás ve tareas L2 ni EXTERNAL_CALLBACK. Los repos tenant-scoped
    existentes NO se relajan.
    """

    @abstractmethod
    async def list_open_l1(
        self,
        tenant_id: UUID | None = None,
        status: str | None = "pending",
        limit: int = 200,
        kind: str | None = None,
    ) -> list[StaffQueueItem]:
        """Cola unificada cross-tenant con contexto de tenant (join barato).

        E6 §3: ``kind`` segmenta la cola — ``approval`` (aprobaciones) vs ``qa``
        (auditoría QA post-COMPLETED). None ⇒ ambos.
        """
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, task_id: UUID) -> HumanTask | None:
        """None si no existe O si está fuera del alcance L1 staff."""
        raise NotImplementedError

    @abstractmethod
    async def find_l1_task_by_case(self, case_id: UUID) -> HumanTask | None:
        """L1 task (stage review_l1 + INTERNAL_QUEUE) ligada a ``case_id``.

        Gate de PII cross-tenant (ADR 0001, alcance 3): el staff solo puede
        leer un caso si existe una tarea L1 servible ligada a él. None ⇒ el
        caso no está en la cola staff ⇒ el caller 404.
        """
        raise NotImplementedError

    @abstractmethod
    async def claim(self, task_id: UUID, actor: str) -> HumanTask | None:
        """UPDATE condicional (lock pesimista §3.2): solo si está ``pending``
        y sin reclamar (o reclamada por el mismo actor). None ⇒ 0 filas."""
        raise NotImplementedError

    @abstractmethod
    async def release(self, task_id: UUID, actor: str, force: bool = False) -> HumanTask | None:
        """Libera el claim — solo el holder, o cualquier staff_admin (force)."""
        raise NotImplementedError
