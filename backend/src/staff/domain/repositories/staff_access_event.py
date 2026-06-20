from abc import ABC, abstractmethod
from uuid import UUID

from src.staff.domain.models.staff_access_event import StaffAccessEvent


class StaffAccessEventRepository(ABC):
    """Audit append-only del plano staff (ADR 0001): sin UPDATE ni DELETE."""

    @abstractmethod
    async def append(self, event: StaffAccessEvent) -> StaffAccessEvent:
        raise NotImplementedError

    @abstractmethod
    async def list(
        self,
        staff_user_id: UUID | None = None,
        tenant_id: UUID | None = None,
        action: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StaffAccessEvent]:
        """Más recientes primero. Para `GET /staff/v1/audit` (staff_admin)."""
        raise NotImplementedError
