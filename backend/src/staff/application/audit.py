"""Lectura del audit staff — solo ``staff_admin`` (ADR 0001, matriz rol×acción)."""

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.staff.domain.exceptions import StaffAdminRequiredError
from src.staff.domain.models.staff_access_event import StaffAccessEvent
from src.staff.domain.models.staff_user import StaffRole, StaffUser
from src.staff.domain.repositories.staff_access_event import StaffAccessEventRepository


@dataclass
class ListStaffAudit(UseCase):
    actor: StaffUser
    repository: StaffAccessEventRepository
    staff_user_id: UUID | None = None
    tenant_id: UUID | None = None
    action: str | None = None
    limit: int = 100
    offset: int = 0

    async def execute(self) -> list[StaffAccessEvent]:
        if self.actor.role is not StaffRole.STAFF_ADMIN:
            raise StaffAdminRequiredError({"role": self.actor.role.value})
        return await self.repository.list(
            staff_user_id=self.staff_user_id,
            tenant_id=self.tenant_id,
            action=self.action,
            limit=self.limit,
            offset=self.offset,
        )
