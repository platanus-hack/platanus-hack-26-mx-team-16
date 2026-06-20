"""Shared loader for the (case, documents) pair returned by the Case CRUD use cases.

The endpoint always renders cases via ``CasePresenter(case, documents)``,
so every Case use case (Creator, Updater, Lister) needs to fetch the
case's documents right after persisting/finding the case. Centralizing
that lookup here keeps the use cases small and prevents the endpoint
from doing side queries.
"""

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.domain.repositories.workflow_document import (
    WorkflowDocumentRepository,
)


@dataclass
class MetaWorkflowCase:
    """A WorkflowCase paired with its current documents — what the
    Case CRUD endpoints render via ``CasePresenter``."""

    case: WorkflowCase
    documents: list[WorkflowDocument]
    # Re-IA 2026-06: algún run de procesamiento FAILED ⇒ badge en la lista.
    # Solo lo puebla el Lister; Creator/Updater lo dejan en False.
    has_failed_runs: bool = False


class CaseDocumentsLoaderMixin:
    """Mixin that adds ``_load_documents_for`` to a use case.

    Subclasses must declare a ``document_repository: WorkflowDocumentRepository``
    field (the dataclass mechanism does the rest). Use it like::

        @dataclass
        class WorkflowCaseUpdater(CaseDocumentsLoaderMixin, UseCase):
            ...
            document_repository: WorkflowDocumentRepository
            ...

            async def execute(self) -> MetaWorkflowCase:
                ...
                return MetaWorkflowCase(
                    case=updated,
                    documents=await self._load_documents_for(case_id, tenant_id),
                )
    """

    document_repository: WorkflowDocumentRepository

    async def _load_documents_for(self, case_id: UUID, tenant_id: UUID) -> list[WorkflowDocument]:
        return await self.document_repository.list_by_case(case_id, tenant_id)
