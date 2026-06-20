from abc import ABC, abstractmethod
from uuid import UUID

from src.staff.domain.entities import StaffCaseAggregate


class StaffCaseReader(ABC):
    """Lector read-only de caso agregado cross-tenant (ADR 0001, alcance 3).

    Única lectura cross-tenant de casos del sistema: resuelve el tenant DESDE
    la fila del caso y carga el resto (docs, runs, análisis, timeline) con
    queries tenant-scoped sobre ese tenant resuelto. Solo lectura.
    """

    @abstractmethod
    async def get_case_aggregate(self, case_id: UUID) -> StaffCaseAggregate | None:
        raise NotImplementedError
