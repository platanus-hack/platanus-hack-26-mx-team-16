"""Re-IA 2026-06 · WorkflowCaseLister + flag ``has_failed_runs``.

El lister marca ``has_failed_runs=True`` solo para los casos cuyo uuid devuelve
``WorkflowProcessingJobRepository.failed_case_ids`` (badge «Procesamiento
fallido» de la lista). Sin repo inyectado (instanciaciones legacy) todos los
casos salen en False. El presenter expone la clave camelCase ``hasFailedRuns``.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from expects import be_false, be_true, equal, expect

from src.common.domain.entities.common.pagination import Page
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.workflows.application.workflow_cases.lister import WorkflowCaseLister
from src.workflows.domain.filters.workflow_case import WorkflowCaseFilters
from src.workflows.presentation.presenters.workflow_case import WorkflowCasePresenter

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")


def _case(name: str) -> WorkflowCase:
    return WorkflowCase(uuid=uuid4(), tenant_id=_TENANT, workflow_id=_WORKFLOW, name=name)


class _FakeCaseRepository:
    def __init__(self, cases: list[WorkflowCase]):
        self.cases = cases

    async def filter_paginated(self, workflow_id, tenant_id, filters):
        return Page(next_cursor=None, items=list(self.cases), limit=filters.limit)


class _FakeDocumentRepository:
    async def list_by_case_ids(self, case_ids, tenant_id):
        return {}


class _FakeProcessingJobRepository:
    def __init__(self, failed: set[UUID]):
        self.failed = failed
        self.seen_case_ids: list[UUID] | None = None

    async def failed_case_ids(self, case_ids, tenant_id):
        self.seen_case_ids = list(case_ids)
        return self.failed


async def test_lister__marks_only_cases_with_failed_jobs():
    # Arrange
    con_fallo, sin_fallo = _case("con fallo"), _case("sin fallo")
    job_repo = _FakeProcessingJobRepository(failed={con_fallo.uuid})

    # Act
    page = await WorkflowCaseLister(
        workflow_id=_WORKFLOW,
        tenant_id=_TENANT,
        filters=WorkflowCaseFilters(),
        case_repository=_FakeCaseRepository([con_fallo, sin_fallo]),
        document_repository=_FakeDocumentRepository(),
        processing_job_repository=job_repo,
    ).execute()

    # Assert
    by_name = {item.case.name: item for item in page.items}
    expect(by_name["con fallo"].has_failed_runs).to(be_true)
    expect(by_name["sin fallo"].has_failed_runs).to(be_false)
    expect(set(job_repo.seen_case_ids or [])).to(equal({con_fallo.uuid, sin_fallo.uuid}))


async def test_lister__without_job_repo_defaults_to_false():
    # Arrange
    case = _case("legacy")

    # Act
    page = await WorkflowCaseLister(
        workflow_id=_WORKFLOW,
        tenant_id=_TENANT,
        filters=WorkflowCaseFilters(),
        case_repository=_FakeCaseRepository([case]),
        document_repository=_FakeDocumentRepository(),
    ).execute()

    # Assert
    expect(page.items[0].has_failed_runs).to(be_false)


def test_presenter__exposes_has_failed_runs_as_camel_case():
    # Arrange
    case = _case("presentado")

    # Act
    presented = WorkflowCasePresenter(instance=case, documents=[], has_failed_runs=True).to_dict
    presented_default = WorkflowCasePresenter(instance=case, documents=[]).to_dict

    # Assert
    expect(presented["hasFailedRuns"]).to(be_true)
    expect(presented_default["hasFailedRuns"]).to(be_false)
