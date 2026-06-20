from dataclasses import dataclass
from uuid import UUID

from src.common.domain.exceptions.processing import CaseNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository


@dataclass
class WorkflowCaseDeleter(UseCase):
    case_id: UUID
    tenant_id: UUID
    case_repository: WorkflowCaseRepository
    # Binding opcional al workflow del path (endpoints JWT): caso de otro
    # workflow del tenant ⇒ 404, no borrable.
    workflow_id: UUID | None = None

    async def execute(self) -> None:
        if self.workflow_id is not None:
            case = await self.case_repository.find_by_id(self.case_id, self.tenant_id)
            if case is None or case.workflow_id != self.workflow_id:
                raise CaseNotFoundError(str(self.case_id))
        await self.case_repository.delete(self.case_id, self.tenant_id)
