"""B1 (cases-table-upload · D3) — guard de editabilidad del nombre del caso.

El nombre solo es editable en workflows dossier (receta con ``await_documents``
⇒ capability ``multi_doc_dossier``). En per_upload el nombre lo fija el archivo
(``_ensure_case``); las altas/renames JWT con nombre se rechazan con 422
``case.name_not_editable``. El rename se rechaza SOLO cuando el nombre cambia
(un echo no-op del nombre en un PUT de status no dispara 422).
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from expects import be_empty, equal, expect, have_length

from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.workflows.application.workflow_cases.creator import WorkflowCaseCreator
from src.workflows.application.workflow_cases.name_editability import (
    CaseNameNotEditableError,
)
from src.workflows.application.workflow_cases.updater import WorkflowCaseUpdater
from src.workflows.domain.models.pipeline import PhaseSpec, PipelineVersion
from src.workflows.domain.recipes import standard_case_phases

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")
_PIPELINE = UUID("66666666-6666-6666-6666-666666666666")
_VERSION_ID = UUID("77777777-7777-7777-7777-777777777777")


def _version(*, with_await: bool) -> PipelineVersion:
    phases = (
        standard_case_phases()
        if with_await
        else [{"id": "analyze", "kind": "analyze", "config": {}}]
    )
    return PipelineVersion(
        uuid=_VERSION_ID,
        pipeline_id=_PIPELINE,
        version=1,
        phases=[PhaseSpec.model_validate(p) for p in phases],
    )


def _case(**overrides) -> WorkflowCase:
    base = dict(uuid=uuid4(), tenant_id=_TENANT, workflow_id=_WORKFLOW, name="Old")
    base.update(overrides)
    return WorkflowCase(**base)


class _FakeCaseRepo:
    def __init__(self, case=None):
        self._case = case
        self.created: list = []
        self.updated: list = []

    async def find_by_id(self, case_id, tenant_id):
        return self._case

    async def create(self, case):
        self.created.append(case)
        self._case = case
        return case

    async def update(self, case):
        self.updated.append(case)
        self._case = case
        return case


class _FakePipelineRepo:
    def __init__(self, version):
        self._version = version

    async def find_by_id(self, pipeline_id, tenant_id):
        return SimpleNamespace(uuid=_PIPELINE, current_version=1)

    async def get_version(self, pipeline_id, version):
        return self._version

    async def find_version_by_id(self, version_id):
        return self._version


class _FakeWorkflowRepo:
    """Workflow con binding a pipeline ⇒ resolución por la rama de binding
    (caso fresco del creator, sin ``pipeline_version_id``)."""

    async def find_by_id(self, workflow_id, tenant_id):
        return SimpleNamespace(uuid=_WORKFLOW, pipeline_id=_PIPELINE)


class _FakeDocRepo:
    async def list_by_case(self, case_id, tenant_id):
        return []


def _creator(name: str, *, with_await: bool) -> WorkflowCaseCreator:
    return WorkflowCaseCreator(
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        name=name,
        case_repository=_FakeCaseRepo(),
        workflow_repository=_FakeWorkflowRepo(),
        document_repository=_FakeDocRepo(),
        pipeline_repository=_FakePipelineRepo(_version(with_await=with_await)),
    )


def _updater(case, name, *, with_await: bool) -> WorkflowCaseUpdater:
    return WorkflowCaseUpdater(
        case_id=case.uuid,
        tenant_id=_TENANT,
        case_repository=_FakeCaseRepo(case),
        document_repository=_FakeDocRepo(),
        pipeline_repository=_FakePipelineRepo(_version(with_await=with_await)),
        name=name,
    )


# ─── B1a · WorkflowCaseCreator (alta JWT) ────────────────────────────────────


async def test_create__rejects_name_on_non_dossier_workflow():
    use_case = _creator("Mi Dossier", with_await=False)

    with pytest.raises(CaseNameNotEditableError) as exc_info:
        await use_case.execute()

    expect(exc_info.value.status_code).to(equal(422))
    expect(exc_info.value.code).to(equal("case.name_not_editable"))
    # No persiste el caso si el nombre no es editable.
    expect(use_case.case_repository.created).to(be_empty)


async def test_create__allows_name_on_dossier_workflow():
    use_case = _creator("Mi Dossier", with_await=True)

    result = await use_case.execute()

    expect(result.case.name).to(equal("Mi Dossier"))
    expect(use_case.case_repository.created).to(have_length(1))


# ─── B1b · WorkflowCaseUpdater (rename JWT) ──────────────────────────────────


async def test_update__rejects_rename_on_non_dossier_workflow():
    case = _case(name="Old", pipeline_version_id=_VERSION_ID)
    use_case = _updater(case, "New", with_await=False)

    with pytest.raises(CaseNameNotEditableError) as exc_info:
        await use_case.execute()

    expect(exc_info.value.status_code).to(equal(422))
    expect(use_case.case_repository.updated).to(be_empty)


async def test_update__allows_rename_on_dossier_workflow():
    case = _case(name="Old", pipeline_version_id=_VERSION_ID)
    use_case = _updater(case, "New", with_await=True)

    result = await use_case.execute()

    expect(result.case.name).to(equal("New"))
    expect(use_case.case_repository.updated).to(have_length(1))


async def test_update__name_echo_unchanged_does_not_check_editability():
    # Un PUT de status que reenvía el mismo name no debe disparar 422 aunque el
    # workflow no sea dossier (el nombre no cambia).
    case = _case(name="Old", pipeline_version_id=_VERSION_ID)
    use_case = _updater(case, "Old", with_await=False)

    result = await use_case.execute()

    expect(result.case.name).to(equal("Old"))
    expect(use_case.case_repository.updated).to(have_length(1))
