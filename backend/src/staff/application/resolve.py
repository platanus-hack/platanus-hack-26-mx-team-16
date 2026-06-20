"""Resolución staff de tareas L1 (ADR 0001, alcance 2).

Reusa ``ResolveHumanTask`` — la MISMA señal ``task_resolved`` de Temporal —
con ``actor=staff:<uuid>`` registrado en ``resolution["resolvedBy"]``. El
stage queda forzado a ``review_l1`` por construcción: la tarea se obtiene
vía ``StaffHumanTaskRepository`` (alcance acotado) y el ``tenant_id`` sale
de la fila, jamás de un header.
"""

from dataclasses import dataclass
from uuid import UUID

from temporalio.client import Client

from src.common.domain.enums.human_tasks import HumanTaskStatus
from src.common.domain.interfaces.use_case import UseCase
from src.staff.application.claim import staff_actor
from src.staff.domain.exceptions import StaffTaskClaimConflictError, StaffTaskNotFoundError
from src.staff.domain.models.staff_user import StaffUser
from src.staff.domain.repositories.staff_human_task import StaffHumanTaskRepository
from src.workflows.application.human_tasks.resolve import ResolveHumanTask
from src.workflows.domain.models.human_task import HumanTask
from src.workflows.domain.repositories.case_event import CaseEventRepository
from src.workflows.domain.repositories.human_task import HumanTaskRepository
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository


@dataclass
class ResolveL1Task(UseCase):
    task_id: UUID
    staff_user: StaffUser
    resolution: dict
    staff_task_repository: StaffHumanTaskRepository
    human_task_repository: HumanTaskRepository
    temporal_client: Client
    # E5 §3.4: el invariante open_flags aplica también al staff L1 (409 +
    # force). None ⇒ check apagado (compat).
    document_repository: WorkflowDocumentRepository | None = None
    # E6 §3: registro del veredicto QA (qa.passed/qa.failed) cuando la task es
    # kind=QA. None ⇒ sin registro (compat).
    case_event_repository: CaseEventRepository | None = None

    async def execute(self) -> HumanTask:
        # Alcance forzado: solo stage=review_l1 + INTERNAL_QUEUE (404 si no).
        task = await self.staff_task_repository.find_by_id(self.task_id)
        if task is None:
            raise StaffTaskNotFoundError(str(self.task_id))

        actor = staff_actor(self.staff_user)
        if task.status is HumanTaskStatus.PENDING:
            # Auto-claim implícito al resolver (E5 §3.2): el UPDATE condicional
            # falla ⇒ otra persona la tiene ⇒ 409 con holder.
            claimed = await self.staff_task_repository.claim(self.task_id, actor)
            if claimed is None:
                fresh = await self.staff_task_repository.find_by_id(self.task_id)
                holder = fresh.claimed_by if fresh else None
                raise StaffTaskClaimConflictError(str(self.task_id), holder=holder)

        resolved = await ResolveHumanTask(
            task_id=self.task_id,
            tenant_id=task.tenant_id,  # de la fila — jamás de un header
            resolution=self.resolution,
            repository=self.human_task_repository,
            temporal_client=self.temporal_client,
            actor=actor,
            document_repository=self.document_repository,
            case_event_repository=self.case_event_repository,
        ).execute()
        if resolved is None:
            raise StaffTaskNotFoundError(str(self.task_id))
        return resolved
