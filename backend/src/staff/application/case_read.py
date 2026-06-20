"""Caso asociado en modo lectura (ADR 0001, alcance 3).

Gate de PII cross-tenant: el contrato del ADR limita la lectura a "el caso
asociado a la tarea". Antes de cargar el agregado se exige que exista una
tarea L1 servible (``stage=review_l1`` + ``INTERNAL_QUEUE``) ligada al caso;
si no, mismo 404 que un caso inexistente — el alcance no se enumera.
"""

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.staff.domain.entities import StaffCaseAggregate
from src.staff.domain.exceptions import StaffCaseNotFoundError
from src.staff.domain.models.staff_user import StaffUser
from src.staff.domain.repositories.staff_case_reader import StaffCaseReader
from src.staff.domain.repositories.staff_human_task import StaffHumanTaskRepository


@dataclass
class GetCaseReadOnly(UseCase):
    case_id: UUID
    staff_user: StaffUser
    reader: StaffCaseReader
    task_repository: StaffHumanTaskRepository

    async def execute(self) -> StaffCaseAggregate:
        # Gate: el staff solo puede leer un caso ligado a una tarea L1 servible.
        # Sin ella ⇒ 404 (no se distingue de un caso inexistente: el alcance
        # cross-tenant no se enumera).
        gate_task = await self.task_repository.find_l1_task_by_case(self.case_id)
        if gate_task is None:
            raise StaffCaseNotFoundError(str(self.case_id))

        aggregate = await self.reader.get_case_aggregate(self.case_id)
        if aggregate is None:
            raise StaffCaseNotFoundError(str(self.case_id))
        return aggregate
