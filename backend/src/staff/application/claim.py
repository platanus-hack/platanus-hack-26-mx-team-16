"""Claim/release de tareas L1 (lock pesimista, diseño E5 §3.2 + ADR 0001).

El claim es un UPDATE condicional en el repo; 0 filas se traduce aquí en el
error correcto: 404 (fuera del alcance L1), 409 ``human_task.already_claimed``
(con holder) o 409 ``human_task.not_claimable`` (ya no está pendiente).
"""

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.staff.domain.exceptions import (
    StaffTaskClaimConflictError,
    StaffTaskNotClaimableError,
    StaffTaskNotFoundError,
)
from src.staff.domain.models.staff_user import StaffRole, StaffUser
from src.staff.domain.repositories.staff_human_task import StaffHumanTaskRepository
from src.workflows.domain.models.human_task import HumanTask


def staff_actor(staff_user: StaffUser) -> str:
    """Formato canónico del actor staff (diseño §3.2): ``staff:<uuid>``."""
    return f"staff:{staff_user.uuid}"


@dataclass
class ClaimL1Task(UseCase):
    task_id: UUID
    staff_user: StaffUser
    repository: StaffHumanTaskRepository
    release: bool = False

    async def execute(self) -> HumanTask:
        actor = staff_actor(self.staff_user)
        if self.release:
            return await self._release(actor)
        return await self._claim(actor)

    async def _claim(self, actor: str) -> HumanTask:
        claimed = await self.repository.claim(self.task_id, actor)
        if claimed is not None:
            return claimed
        task = await self.repository.find_by_id(self.task_id)
        if task is None:
            raise StaffTaskNotFoundError(str(self.task_id))
        if task.claimed_by and task.claimed_by != actor:
            raise StaffTaskClaimConflictError(str(self.task_id), holder=task.claimed_by)
        raise StaffTaskNotClaimableError(str(self.task_id), task.status.value)

    async def _release(self, actor: str) -> HumanTask:
        # Unclaim: solo el holder, o un staff_admin (diseño §3.2).
        force = self.staff_user.role is StaffRole.STAFF_ADMIN
        released = await self.repository.release(self.task_id, actor, force=force)
        if released is not None:
            return released
        task = await self.repository.find_by_id(self.task_id)
        if task is None:
            raise StaffTaskNotFoundError(str(self.task_id))
        raise StaffTaskClaimConflictError(str(self.task_id), holder=task.claimed_by)
