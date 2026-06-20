"""Fetch a WorkflowCase enriched with its document groups for the detail view."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.common.domain.exceptions.processing import CaseNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.workflows.application.workflow_cases._documents_loader import (
    CaseDocumentsLoaderMixin,
)
from src.workflows.domain.models.case_event import CaseEvent
from src.workflows.domain.others_document_type import build_document_groups
from src.workflows.domain.repositories.case_event import CaseEventRepository
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.domain.repositories.workflow_document import (
    WorkflowDocumentRepository,
)


@dataclass
class CaseDetailView:
    case: WorkflowCase
    document_groups: list[Any]
    timeline: list[CaseEvent] | None = None  # case_events desc, límite 50 (E4)
    # E5 · fan-out: {status: n} de los children (vacío si no es padre).
    children_by_status: dict[str, int] | None = None


@dataclass
class WorkflowCaseGetter(CaseDocumentsLoaderMixin, UseCase):
    case_id: UUID
    tenant_id: UUID
    case_repository: WorkflowCaseRepository
    document_repository: WorkflowDocumentRepository
    document_type_repository: DocumentTypeRepository
    # E4: timeline opcional para no romper instanciaciones existentes.
    case_event_repository: CaseEventRepository | None = None
    # Binding opcional al workflow del path (endpoints JWT): caso de otro
    # workflow del tenant ⇒ 404.
    workflow_id: UUID | None = None

    async def execute(self) -> CaseDetailView:
        case = await self.case_repository.find_by_id(self.case_id, self.tenant_id)
        if not case:
            raise CaseNotFoundError(str(self.case_id))
        if self.workflow_id is not None and case.workflow_id != self.workflow_id:
            raise CaseNotFoundError(str(self.case_id))

        documents = await self._load_documents_for(self.case_id, self.tenant_id)
        document_types = await self.document_type_repository.list_by_workflow(case.workflow_id, self.tenant_id)

        document_groups = build_document_groups(
            document_types=document_types,
            documents=documents,
            tenant_id=self.tenant_id,
            workflow_id=case.workflow_id,
        )
        timeline: list[CaseEvent] = []
        if self.case_event_repository is not None:
            timeline = await self.case_event_repository.list_by_case(
                self.case_id, self.tenant_id, limit=50, desc=True
            )
        children_by_status = await self.case_repository.count_children_by_status(
            self.case_id, self.tenant_id
        )
        return CaseDetailView(
            case=case,
            document_groups=document_groups,
            timeline=timeline,
            children_by_status=children_by_status,
        )
