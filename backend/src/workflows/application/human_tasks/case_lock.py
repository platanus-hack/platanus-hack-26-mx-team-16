"""Lock pesimista por caso (E5 · diseño §3.2) — helper REUTILIZABLE.

Mientras la tarea APPROVAL abierta de un caso esté reclamada por X, cualquier
mutación del caso por otro actor (PATCH de campos del Inspection Bench,
corrections M2M…) responde 423 ``case.locked`` con el holder. Un único punto
de verdad: el claim de la HumanTask — no hay columna de lock en
``workflow_cases``.
"""

from __future__ import annotations

from uuid import UUID

from src.common.domain.enums.human_tasks import HumanTaskKind
from src.common.domain.exceptions._base import DomainError
from src.workflows.domain.models.human_task import HumanTask
from src.workflows.domain.repositories.human_task import HumanTaskRepository


class CaseLockedError(DomainError):
    """La APPROVAL abierta del caso está reclamada por otro actor (§3.2)."""

    def __init__(self, case_id: str, holder: str):
        super().__init__(
            code="case.locked",
            message=f"The case review is claimed by another actor: {holder}.",
            status_code=423,
            context={"case_id": case_id, "holder": holder},
        )


async def find_open_approval_task(
    repository: HumanTaskRepository, case_id: UUID, tenant_id: UUID
) -> HumanTask | None:
    """La APPROVAL PENDING más antigua del caso (la del stage en curso)."""
    tasks = await repository.list_open_by_case(case_id, tenant_id)
    for task in tasks:
        if task.kind == HumanTaskKind.APPROVAL:
            return task
    return None


async def ensure_case_not_locked(
    repository: HumanTaskRepository, case_id: UUID, tenant_id: UUID, actor: str
) -> HumanTask | None:
    """423 ``case.locked`` si la APPROVAL abierta está reclamada por OTRO.

    Devuelve la APPROVAL abierta (o ``None``) para que el caller reuse la fila
    (señal ``corrections``, derivar el level del stage…) sin re-consultar.
    """
    approval = await find_open_approval_task(repository, case_id, tenant_id)
    if approval is not None and approval.claimed_by and approval.claimed_by != actor:
        raise CaseLockedError(str(case_id), approval.claimed_by)
    return approval
