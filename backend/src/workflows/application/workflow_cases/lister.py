from dataclasses import dataclass
from uuid import UUID

from src.common.domain.entities.common.pagination import Page
from src.common.domain.interfaces.use_case import UseCase
from src.workflows.application.workflow_cases._documents_loader import MetaWorkflowCase
from src.workflows.domain.filters.workflow_case import WorkflowCaseFilters
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository
from src.workflows.domain.repositories.workflow_processing_job_repository import (
    WorkflowProcessingJobRepository,
)


@dataclass
class WorkflowCaseLister(UseCase):
    """List a workflow's cases with their documents already attached.

    Avoids the N+1 lookup pattern (``for case in cases: list_by_case(case)``)
    by fetching all documents for the page in a single ``list_by_case_ids``
    query grouped by case_id in the repository.
    """

    workflow_id: UUID
    tenant_id: UUID
    filters: WorkflowCaseFilters
    case_repository: WorkflowCaseRepository
    document_repository: WorkflowDocumentRepository
    # Re-IA 2026-06: opcional para no romper instanciaciones existentes; sin él
    # los casos salen con has_failed_runs=False (el endpoint SÍ lo inyecta).
    processing_job_repository: WorkflowProcessingJobRepository | None = None

    async def execute(self) -> Page[MetaWorkflowCase]:
        page = await self.case_repository.filter_paginated(
            workflow_id=self.workflow_id,
            tenant_id=self.tenant_id,
            filters=self.filters,
        )

        if not page.items:
            return page  # type: ignore[return-value]

        case_ids = [case.uuid for case in page.items]
        documents_by_case = await self.document_repository.list_by_case_ids(case_ids, self.tenant_id)

        failed_ids: set[UUID] = set()
        if self.processing_job_repository is not None:
            failed_ids = await self.processing_job_repository.failed_case_ids(case_ids, self.tenant_id)

        page.items = [
            MetaWorkflowCase(
                case=case,
                documents=documents_by_case.get(case.uuid, []),
                has_failed_runs=case.uuid in failed_ids,
            )
            for case in page.items
        ]
        return page  # type: ignore[return-value]
