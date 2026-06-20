from abc import ABC, abstractmethod
from uuid import UUID

from src.staff.domain.models.staff_user import StaffUser


class StaffUserRepository(ABC):
    """Identidad staff de plataforma (ADR 0001). Fuente de verdad revocable:
    sin fila activa no hay acceso, sin importar qué diga el token."""

    @abstractmethod
    async def find_active_by_user_id(self, user_id: UUID) -> StaffUser | None:
        """Fila ``status=active`` del user — la consulta por request de
        ``StaffUserDep`` (revocación inmediata) y la emisión del claim."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_user_id(self, user_id: UUID) -> StaffUser | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, staff_user_id: UUID) -> StaffUser | None:
        raise NotImplementedError

    @abstractmethod
    async def add(self, staff_user: StaffUser) -> StaffUser:
        raise NotImplementedError

    @abstractmethod
    async def update(self, staff_user: StaffUser) -> StaffUser:
        """Persiste la entidad completa (rol, status, revoked_at)."""
        raise NotImplementedError
