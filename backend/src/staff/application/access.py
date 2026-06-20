"""Alta y revocación de staff (ADR 0001).

El staff se revoca, nunca se borra: ``StaffUserDep`` consulta la fila activa
por request, así que la revocación corta el acceso aunque el JWT con
``is_staff`` siga vivo. ``GrantStaffAccess`` es idempotente: re-otorgar
reactiva la fila revocada y/o actualiza el rol.
"""

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.common.application.helpers.datetimes import utc_now
from src.common.domain.interfaces.use_case import UseCase
from src.staff.domain.models.staff_user import StaffRole, StaffUser, StaffUserStatus
from src.staff.domain.repositories.staff_user import StaffUserRepository


@dataclass
class GrantStaffAccess(UseCase):
    user_id: UUID
    role: StaffRole
    repository: StaffUserRepository

    async def execute(self) -> StaffUser:
        existing = await self.repository.find_by_user_id(self.user_id)
        if existing is None:
            return await self.repository.add(
                StaffUser(uuid=uuid4(), user_id=self.user_id, role=self.role)
            )
        if existing.role is self.role and existing.is_active:
            return existing  # idempotente
        return await self.repository.update(
            existing.model_copy(
                update={"role": self.role, "status": StaffUserStatus.ACTIVE, "revoked_at": None}
            )
        )


@dataclass
class RevokeStaffAccess(UseCase):
    user_id: UUID
    repository: StaffUserRepository

    async def execute(self) -> StaffUser | None:
        existing = await self.repository.find_by_user_id(self.user_id)
        if existing is None or not existing.is_active:
            return existing  # idempotente
        return await self.repository.update(
            existing.model_copy(
                update={"status": StaffUserStatus.REVOKED, "revoked_at": utc_now()}
            )
        )
