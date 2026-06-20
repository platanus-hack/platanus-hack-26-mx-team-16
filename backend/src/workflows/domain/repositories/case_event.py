from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.workflows.domain.models.case_event import CaseEvent


class CaseEventRepository(ABC):
    """Timeline append-only del caso (E4): solo create + list, nunca update."""

    @abstractmethod
    async def create(self, event: CaseEvent) -> CaseEvent:
        raise NotImplementedError

    @abstractmethod
    async def list_by_case(
        self,
        case_id: UUID,
        tenant_id: UUID,
        limit: int = 50,
        desc: bool = True,
    ) -> list[CaseEvent]:
        raise NotImplementedError

    @abstractmethod
    async def count_by_type_since(
        self,
        types: list[str],
        since: datetime,
        tenant_id: UUID | None = None,
    ) -> list[tuple[UUID, str, str | None, int]]:
        """Agregado cross-case para las métricas QA (E6 · §3.5).

        Cuenta eventos de los ``types`` dados desde ``since``, agrupados por
        ``(tenant_id, type, actor)``. ``tenant_id=None`` ⇒ cross-tenant (plano
        staff). Usa el índice ``(tenant_id, type, created_at)`` de la migración
        E6. Devuelve filas ``(tenant_id, type, actor, count)``.
        """
        raise NotImplementedError
