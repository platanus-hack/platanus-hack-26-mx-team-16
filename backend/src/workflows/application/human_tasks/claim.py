"""Claim/release tenant de una HumanTask (E5 · diseño §3.2).

Lock pesimista: el claim es un UPDATE condicional en el repo (``status=pending
AND (claimed_by IS NULL OR claimed_by=actor)``); 0 filas se traduce aquí en el
error correcto — 404 (no existe), 409 ``human_task.already_claimed`` (con
holder) o 409 ``human_task.not_claimable`` (ya no está pendiente). El release
solo lo hace el holder o un tenant owner/admin (``force``).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.exceptions._base import DomainError
from src.common.domain.interfaces.use_case import UseCase
from src.workflows.application.human_tasks.resolve import HumanTaskClaimConflictError
from src.workflows.domain.models.human_task import HumanTask
from src.workflows.domain.repositories.human_task import HumanTaskRepository


class HumanTaskNotFoundError(DomainError):
    def __init__(self, task_id: str):
        super().__init__(
            code="human_task.not_found",
            message="Human task not found",
            status_code=404,
            context={"task_id": task_id},
        )


class HumanTaskNotClaimableError(DomainError):
    def __init__(self, task_id: str, status: str):
        super().__init__(
            code="human_task.not_claimable",
            message=f"The task is no longer claimable (status={status}).",
            status_code=409,
            context={"task_id": task_id, "status": status},
        )


@dataclass
class ClaimHumanTask(UseCase):
    task_id: UUID
    tenant_id: UUID
    actor: str  # "user:<uuid>"
    repository: HumanTaskRepository
    release: bool = False
    # Release ajeno: solo tenant owner/admin (lo decide el endpoint).
    force_release: bool = False

    async def execute(self) -> HumanTask:
        if self.release:
            return await self._release()
        return await self._claim()

    async def _claim(self) -> HumanTask:
        claimed = await self.repository.claim(self.task_id, self.tenant_id, self.actor)
        if claimed is not None:
            return claimed
        task = await self.repository.find_by_id(self.task_id, self.tenant_id)
        if task is None:
            raise HumanTaskNotFoundError(str(self.task_id))
        if task.claimed_by and task.claimed_by != self.actor:
            raise HumanTaskClaimConflictError(str(self.task_id), holder=task.claimed_by)
        raise HumanTaskNotClaimableError(str(self.task_id), task.status.value)

    async def _release(self) -> HumanTask:
        released = await self.repository.release(
            self.task_id, self.tenant_id, self.actor, force=self.force_release
        )
        if released is not None:
            return released
        task = await self.repository.find_by_id(self.task_id, self.tenant_id)
        if task is None:
            raise HumanTaskNotFoundError(str(self.task_id))
        raise HumanTaskClaimConflictError(str(self.task_id), holder=task.claimed_by)
