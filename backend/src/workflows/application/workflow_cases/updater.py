from dataclasses import dataclass
from uuid import UUID, uuid4

from src.common.domain.enums.workflow_cases import WorkflowCaseStatus
from src.common.domain.exceptions.processing import CaseNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.workflows.application.workflow_cases._documents_loader import (
    CaseDocumentsLoaderMixin,
    MetaWorkflowCase,
)
from src.workflows.application.workflow_cases.name_editability import (
    CaseNameNotEditableError,
    case_name_is_editable,
)
from src.workflows.domain.models.case_event import CaseEvent
from src.workflows.domain.repositories.case_event import CaseEventRepository
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.domain.repositories.workflow_document import (
    WorkflowDocumentRepository,
)
from src.workflows.domain.services.case_state_machine import assert_transition


@dataclass
class WorkflowCaseUpdater(CaseDocumentsLoaderMixin, UseCase):
    case_id: UUID
    tenant_id: UUID
    case_repository: WorkflowCaseRepository
    document_repository: WorkflowDocumentRepository
    pipeline_repository: PipelineRepository
    name: str | None = None
    status: WorkflowCaseStatus | None = None
    # E4: timeline append-only; opcional para no romper instanciaciones viejas.
    case_event_repository: CaseEventRepository | None = None
    actor: str | None = None
    # Binding opcional al workflow del path (endpoints JWT): caso de otro
    # workflow del tenant ⇒ 404.
    workflow_id: UUID | None = None
    workflow_repository: WorkflowRepository | None = None

    async def execute(self) -> MetaWorkflowCase:
        case = await self.case_repository.find_by_id(self.case_id, self.tenant_id)
        if not case:
            raise CaseNotFoundError(str(self.case_id))
        if self.workflow_id is not None and case.workflow_id != self.workflow_id:
            raise CaseNotFoundError(str(self.case_id))

        status_changed = False
        previous_status = case.status
        if self.name is not None and self.name != case.name:
            # B1b (D3): el rename solo aplica en workflows dossier
            # (await_documents). Se rechaza solo cuando el nombre cambia, para
            # no romper un echo no-op de name en un PUT de status.
            if not await case_name_is_editable(
                case, self.tenant_id, self.pipeline_repository, self.workflow_repository
            ):
                raise CaseNameNotEditableError(str(self.case_id))
            case.name = self.name
        if self.status is not None and self.status != case.status:
            # E4 · diseño §1: el PUT pasa por la máquina (409 si es ilegal).
            assert_transition(case.status, self.status)
            case.status = self.status
            status_changed = True

        updated = await self.case_repository.update(case)
        if status_changed and self.case_event_repository is not None:
            await self.case_event_repository.create(
                CaseEvent(
                    uuid=uuid4(),
                    tenant_id=self.tenant_id,
                    case_id=self.case_id,
                    type="status.changed",
                    payload={"from": previous_status.value, "to": updated.status.value},
                    actor=self.actor,
                )
            )
        documents = await self._load_documents_for(self.case_id, self.tenant_id)
        return MetaWorkflowCase(case=updated, documents=documents)
