from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.workflows.application.workflow_cases._documents_loader import (
    CaseDocumentsLoaderMixin,
    MetaWorkflowCase,
)
from src.workflows.application.workflow_cases.name_editability import (
    CaseNameNotEditableError,
    case_name_is_editable,
)
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.domain.repositories.workflow_document import (
    WorkflowDocumentRepository,
)


@dataclass
class WorkflowCaseCreator(CaseDocumentsLoaderMixin, UseCase):
    tenant_id: UUID
    workflow_id: UUID
    name: str
    case_repository: WorkflowCaseRepository
    workflow_repository: WorkflowRepository
    document_repository: WorkflowDocumentRepository
    pipeline_repository: PipelineRepository
    created_by: UUID | None = None

    async def execute(self) -> MetaWorkflowCase:
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if not workflow:
            raise WorkflowNotFoundError(str(self.workflow_id))

        now = datetime.now(UTC)
        case = WorkflowCase(
            uuid=uuid4(),
            tenant_id=self.tenant_id,
            workflow_id=self.workflow_id,
            name=self.name,
            created_by=self.created_by,
            created_at=now,
            updated_at=now,
        )
        # B1a (D3): nombrar al crear solo es válido en workflows dossier
        # (await_documents). En per_upload el caso lo mina el dispatcher con el
        # nombre del archivo; un alta JWT con nombre explícito se rechaza.
        if not await case_name_is_editable(
            case, self.tenant_id, self.pipeline_repository, self.workflow_repository
        ):
            raise CaseNameNotEditableError(str(case.uuid))
        created = await self.case_repository.create(case)
        documents = await self._load_documents_for(created.uuid, self.tenant_id)
        return MetaWorkflowCase(case=created, documents=documents)
