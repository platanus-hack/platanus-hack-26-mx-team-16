"""E4 · EnsureCaseRunStarted: arranque idempotente del run CASE#.

Solo recetas con ``await_documents`` arrancan el CASE# (scope="case",
id determinista ``CASE#{uuid.hex}``); sella ``pipeline_version_id`` si era
NULL; ``WorkflowAlreadyStarted`` se ignora.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

from expects import be_empty, be_false, be_none, be_true, equal, expect, have_length
from temporalio.exceptions import WorkflowAlreadyStartedError

from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.workflows.application.workflow_cases.case_run_starter import (
    EnsureCaseRunStarted,
    case_run_workflow_id,
    signal_case_run,
)
from src.workflows.domain.models.pipeline import PhaseSpec, PipelineVersion
from src.workflows.domain.recipes import standard_case_phases

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")
_PIPELINE = UUID("66666666-6666-6666-6666-666666666666")
_VERSION_ID = UUID("77777777-7777-7777-7777-777777777777")


def _version(*, with_await: bool = True) -> PipelineVersion:
    phases = standard_case_phases() if with_await else [{"id": "analyze", "kind": "analyze", "config": {}}]
    return PipelineVersion(
        uuid=_VERSION_ID,
        pipeline_id=_PIPELINE,
        version=3,
        phases=[PhaseSpec.model_validate(p) for p in phases],
    )


def _case(**overrides) -> WorkflowCase:
    base = dict(uuid=uuid4(), tenant_id=_TENANT, workflow_id=_WORKFLOW, name="Case")
    base.update(overrides)
    return WorkflowCase(**base)


class _FakeCaseRepo:
    def __init__(self, case):
        self._case = case
        self.updated: list = []

    async def find_by_id(self, case_id, tenant_id):
        return self._case

    async def update(self, case):
        self.updated.append(case)
        return case


class _FakePipelineRepo:
    def __init__(self, version):
        self._version = version

    async def find_by_id(self, pipeline_id, tenant_id):
        return SimpleNamespace(uuid=_PIPELINE, current_version=3)

    async def get_version(self, pipeline_id, version):
        return self._version

    async def find_version_by_id(self, version_id):
        return self._version


class _FakeTemporalClient:
    def __init__(self, already_started: bool = False):
        self.already_started = already_started
        self.started: list = []
        self.signals: list = []

    async def start_workflow(self, run_method, payload, *, id, task_queue):
        if self.already_started:
            raise WorkflowAlreadyStartedError(id, "PipelineInterpreterWorkflow")
        self.started.append((payload, id, task_queue))

    def get_workflow_handle(self, workflow_id):
        signals = self.signals

        class _Handle:
            async def signal(self, name, *args):
                signals.append((workflow_id, name, args))

        return _Handle()


def _use_case(case, version, client) -> EnsureCaseRunStarted:
    return EnsureCaseRunStarted(
        tenant_id=_TENANT,
        case_id=case.uuid,
        case_repository=_FakeCaseRepo(case),
        pipeline_repository=_FakePipelineRepo(version),
        temporal_client=client,
        task_queue="q",
    )


async def test_ensure__starts_case_run_with_case_scope_and_seals_version():
    case = _case(pipeline_id=_PIPELINE, pipeline_version_id=None)
    client = _FakeTemporalClient()
    repo = _FakeCaseRepo(case)
    use_case = EnsureCaseRunStarted(
        tenant_id=_TENANT,
        case_id=case.uuid,
        case_repository=repo,
        pipeline_repository=_FakePipelineRepo(_version()),
        temporal_client=client,
        task_queue="q",
    )

    result = await use_case.execute()

    expect(result.started).to(be_true)
    expect(result.has_await_documents).to(be_true)
    expect(result.run_id).to(equal(f"CASE#{case.uuid.hex}"))

    payload, workflow_id, task_queue = client.started[0]
    expect(workflow_id).to(equal(case_run_workflow_id(case.uuid)))
    expect(payload.scope).to(equal("case"))
    expect(payload.pipeline_id).to(equal(_PIPELINE))
    expect(payload.version).to(equal(3))
    expect(payload.document.case_id).to(equal(case.uuid))
    expect(payload.document.job_id).to(equal(workflow_id))

    # Sella la versión al arrancar (era NULL).
    expect(repo.updated).to(have_length(1))
    expect(repo.updated[0].pipeline_version_id).to(equal(_VERSION_ID))


async def test_ensure__noop_when_recipe_has_no_await_documents():
    case = _case(pipeline_id=_PIPELINE)
    client = _FakeTemporalClient()

    result = await _use_case(case, _version(with_await=False), client).execute()

    expect(result.started).to(be_false)
    expect(result.has_await_documents).to(be_false)
    expect(client.started).to(be_empty)


async def test_ensure__ignores_workflow_already_started():
    case = _case(pipeline_id=_PIPELINE, pipeline_version_id=_VERSION_ID)
    client = _FakeTemporalClient(already_started=True)

    result = await _use_case(case, _version(), client).execute()

    expect(result.started).to(be_false)
    expect(result.has_await_documents).to(be_true)


async def test_ensure__no_recipe_resolvable_is_clean_noop():
    case = _case()  # sin pipeline_id ni versión sellada ni workflow_repository

    class _EmptyPipelineRepo(_FakePipelineRepo):
        async def find_version_by_id(self, version_id):
            return None

        async def find_by_id(self, pipeline_id, tenant_id):
            return None

    client = _FakeTemporalClient()
    use_case = EnsureCaseRunStarted(
        tenant_id=_TENANT,
        case_id=case.uuid,
        case_repository=_FakeCaseRepo(case),
        pipeline_repository=_EmptyPipelineRepo(None),
        temporal_client=client,
        task_queue="q",
    )

    result = await use_case.execute()

    expect(result.started).to(be_false)
    expect(result.run_id).to(be_none)
    expect(client.started).to(be_empty)


async def test_signal_case_run__signals_case_workflow_and_swallows_errors():
    client = _FakeTemporalClient()
    case_id = uuid4()

    sent = await signal_case_run(client, case_id, "case_docs_changed")

    expect(sent).to(be_true)
    workflow_id, name, args = client.signals[0]
    expect(workflow_id).to(equal(f"CASE#{case_id.hex}"))
    expect(name).to(equal("case_docs_changed"))
    expect(args).to(equal(()))

    class _BrokenClient:
        def get_workflow_handle(self, workflow_id):
            raise RuntimeError("temporal down")

    # Best-effort: jamás levanta.
    expect(await signal_case_run(_BrokenClient(), case_id, "case_ready", {"force": True})).to(be_false)
