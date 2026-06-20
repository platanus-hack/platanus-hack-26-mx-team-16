"""Lister use case for WorkflowProcessingJobs enriched with documents."""

from dataclasses import dataclass, field
from uuid import UUID

from src.common.domain.entities.common.pagination import Page
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.workflows.domain.filters.workflow_processing_job import WorkflowProcessingJobFilters
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository
from src.workflows.domain.repositories.workflow_processing_job_repository import (
    WorkflowProcessingJobRepository,
)


@dataclass
class WorkflowProcessingJobView:
    """A `WorkflowProcessingJob` plus the related rows the listing UI needs."""

    processing_job: WorkflowProcessingJob
    file_name: str | None
    documents: list[WorkflowDocument] = field(default_factory=list)


@dataclass
class WorkflowProcessingJobLister(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    filters: WorkflowProcessingJobFilters
    processing_job_repository: WorkflowProcessingJobRepository
    document_repository: WorkflowDocumentRepository

    async def execute(self) -> Page[WorkflowProcessingJobView]:
        page = await self.processing_job_repository.filter_paginated(
            workflow_id=self.workflow_id,
            tenant_id=self.tenant_id,
            filters=self.filters,
        )

        if not page.items:
            return page  # type: ignore[return-value]

        set_uuids = [s.uuid for s in page.items]
        doc_rows = await self.document_repository.list_by_processing_job_ids(set_uuids, self.tenant_id)

        docs_by_set: dict[UUID, list[WorkflowDocument]] = {}
        for doc in doc_rows:
            if doc.processing_job_id:
                docs_by_set.setdefault(doc.processing_job_id, []).append(doc)

        views = [
            WorkflowProcessingJobView(
                processing_job=s,
                file_name=s.file_name,
                documents=docs_by_set.get(s.uuid, []),
            )
            for s in page.items
        ]

        return Page(
            items=views,
            next_cursor=page.next_cursor,
            limit=page.limit,
        )
