"""E4 · routing de POST /v1/cases/{id}/data (SubmitCaseData).

Receta CON ``await_documents`` ⇒ nada de runs DATA#: asegura el CASE# y señala
``case_docs_changed`` (best-effort). Sin ``await_documents`` ⇒ comportamiento
E3 intacto (``_start_data_run``).
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from expects import be_empty, equal, expect, have_length

from src.common.domain.enums.workflows import WorkflowDocumentStatus
from src.common.domain.exceptions.processing import WorkflowPipelineNotConfiguredError
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.workflows.application.workflow_cases.m2m import SubmitCaseData
from src.workflows.domain.models.pipeline import PhaseSpec, PipelineVersion
from src.workflows.domain.recipes import (
    data_analysis_phases,
    standard_case_phases,
    standard_extraction_phases,
)

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")
_PIPELINE = UUID("66666666-6666-6666-6666-666666666666")
_TYPE_DATOS = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _version(phases: list[dict]) -> PipelineVersion:
    return PipelineVersion(
        uuid=uuid4(),
        pipeline_id=_PIPELINE,
        version=1,
        phases=[PhaseSpec.model_validate(p) for p in phases],
    )


class _FakeCaseRepo:
    def __init__(self, case):
        self._case = case

    async def find_by_id(self, case_id, tenant_id):
        return self._case

    async def update(self, case):
        self._case = case
        return case


class _FakeDocRepo:
    async def create(self, document):
        document.status = WorkflowDocumentStatus.EXTRACTED
        return document


class _FakeDocTypeRepo:
    async def list_by_workflow(self, workflow_id, tenant_id):
        return [SimpleNamespace(uuid=_TYPE_DATOS, slug="datos_validados", current_version=1)]


class _FakePipelineRepo:
    def __init__(self, version):
        self._version = version

    async def find_by_id(self, pipeline_id, tenant_id):
        return SimpleNamespace(uuid=_PIPELINE, current_version=1)

    async def find_by_workflow(self, workflow_id, tenant_id):
        # ADR 0002: el caso corre el pipeline PROPIO de su workflow.
        return SimpleNamespace(uuid=_PIPELINE, current_version=1)

    async def get_version(self, pipeline_id, version):
        return self._version

    async def find_version_by_id(self, version_id):
        return self._version


class _FakeTemporalClient:
    def __init__(self):
        self.started: list = []
        self.signals: list = []

    async def start_workflow(self, run_method, payload, *, id, task_queue):
        self.started.append((payload, id))

    def get_workflow_handle(self, workflow_id):
        signals = self.signals

        class _Handle:
            async def signal(self, name, *args):
                signals.append((workflow_id, name, args))

        return _Handle()


def _use_case(case, version, client) -> SubmitCaseData:
    return SubmitCaseData(
        tenant_id=_TENANT,
        case_id=case.uuid,
        doc_type_slug="datos_validados",
        payload={"total": 100},
        case_repository=_FakeCaseRepo(case),
        document_repository=_FakeDocRepo(),
        document_type_repository=_FakeDocTypeRepo(),
        pipeline_repository=_FakePipelineRepo(version),
        temporal_client=client,
        task_queue="q",
    )


async def test_submit__await_documents_recipe_signals_case_run_instead_of_data_run():
    case = WorkflowCase(
        uuid=uuid4(), tenant_id=_TENANT, workflow_id=_WORKFLOW, name="C", pipeline_id=_PIPELINE
    )
    client = _FakeTemporalClient()

    result = await _use_case(case, _version(standard_case_phases()), client).execute()

    # Sin run DATA#; el CASE# se asegura (start idempotente) y recibe la señal.
    expect(result.job_id).to(equal(""))
    data_runs = [job for _p, job in client.started if job.startswith("DATA#")]
    expect(data_runs).to(be_empty)
    case_runs = [job for _p, job in client.started if job == f"CASE#{case.uuid.hex}"]
    expect(case_runs).to(have_length(1))
    expect(client.signals).to(have_length(1))
    workflow_id, name, _args = client.signals[0]
    expect(workflow_id).to(equal(f"CASE#{case.uuid.hex}"))
    expect(name).to(equal("case_docs_changed"))


async def test_submit__data_only_recipe_keeps_e3_data_run():
    case = WorkflowCase(
        uuid=uuid4(), tenant_id=_TENANT, workflow_id=_WORKFLOW, name="C", pipeline_id=_PIPELINE
    )
    client = _FakeTemporalClient()

    result = await _use_case(case, _version(data_analysis_phases()), client).execute()

    expect(result.job_id.startswith(f"DATA#{case.uuid.hex}")).to(equal(True))
    expect(client.signals).to(be_empty)
    payload, job_id = client.started[0]
    expect(job_id).to(equal(result.job_id))
    expect(payload.scope).to(equal(None))  # full run E3 intacto
    # ADR 0002 · §3.6: el run data-only entra al pipeline propio del workflow
    # por el sub-segmento ``data`` (desde la primera fase ``analyze``).
    expect(payload.entry_point).to(equal("data"))


async def test_submit__pipeline_without_analyze_phase_is_409():
    # ADR 0002 · zanjado #2: POST /v1/cases/{id}/data sobre un pipeline SIN
    # fase ``analyze`` (p.ej. extracción estándar) es un error de configuración
    # (409), no un dispatch al vacío. ``standard_extraction_phases`` no tiene
    # ``await_documents`` ⇒ cae a ``_start_data_run`` ⇒ select_phases(DATA) vacío.
    case = WorkflowCase(
        uuid=uuid4(), tenant_id=_TENANT, workflow_id=_WORKFLOW, name="C", pipeline_id=_PIPELINE
    )
    client = _FakeTemporalClient()

    use_case = _use_case(case, _version(standard_extraction_phases()), client)

    with pytest.raises(WorkflowPipelineNotConfiguredError):
        await use_case.execute()
    expect(client.started).to(be_empty)
    expect(client.signals).to(be_empty)
