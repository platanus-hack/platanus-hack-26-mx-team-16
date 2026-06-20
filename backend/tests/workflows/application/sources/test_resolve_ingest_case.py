"""E4 · ResolveIngestCase: vínculo ingest → caso (spec source_webhooks §7.2/§7.3).

``caseId`` debe existir en el workflow del source (400 ``ingest.CaseNotFound``);
``caseName`` hace find-or-create por ``external_ref`` (único por workflow, con
retry de carrera); sin referencia ⇒ no-op (set anónimo). ``case.created`` SOLO
en creación real; ``EnsureCaseRunStarted`` tras crear/encontrar (CASE# si la
receta tiene ``await_documents``). Workflow STANDARD + referencia ⇒ 400
``ingest.CaseNotAllowed``.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from expects import be_empty, be_false, be_none, be_true, equal, expect, have_length
from sqlalchemy.exc import IntegrityError

from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.connections.domain.exceptions import (
    IngestCaseNotAllowedError,
    IngestCaseNotFoundError,
)
from src.workflows.application.sources.ingest import ResolveIngestCase
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


def _existing_case(**overrides) -> WorkflowCase:
    base = dict(
        uuid=uuid4(),
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        name="EXP-1",
        external_ref="EXP-1",
    )
    base.update(overrides)
    return WorkflowCase(**base)


class _FakeWorkflowRepo:
    # E7 · F2: la ingesta con caso ya no mira `workflow_type` (caso universal);
    # ``missing=True`` simula un workflow inexistente (único rechazo restante).
    def __init__(self, pipeline_id: UUID | None = _PIPELINE, *, missing: bool = False):
        self._workflow = (
            None if missing else SimpleNamespace(uuid=_WORKFLOW, pipeline_id=pipeline_id)
        )

    async def find_by_id(self, workflow_id, tenant_id):
        return self._workflow


class _FakeCaseRepo:
    def __init__(self, existing: WorkflowCase | None = None, race: bool = False):
        self._existing = existing
        self._race = race
        self._finds = 0
        self.created: list[WorkflowCase] = []
        self.updated: list[WorkflowCase] = []

    async def find_by_id(self, case_id, tenant_id):
        for case in [*self.created, self._existing]:
            if case is not None and case.uuid == case_id:
                return case
        return None

    async def find_by_external_ref(self, workflow_id, external_ref, tenant_id):
        self._finds += 1
        if self._race and self._finds == 1:
            return None  # otro request gana la carrera entre el find y el insert
        if self._existing is not None and self._existing.external_ref == external_ref:
            return self._existing
        return None

    async def create(self, case):
        if self._race:
            raise IntegrityError("INSERT INTO workflow_cases", {}, Exception("duplicate key"))
        self.created.append(case)
        return case

    async def update(self, case):
        self.updated.append(case)
        return case


class _FakePipelineRepo:
    def __init__(self, version: PipelineVersion):
        self._version = version

    async def find_by_id(self, pipeline_id, tenant_id):
        return SimpleNamespace(uuid=_PIPELINE, current_version=3)

    async def find_by_slug(self, slug, tenant_id):
        return SimpleNamespace(uuid=_PIPELINE, current_version=3)

    async def get_version(self, pipeline_id, version):
        return self._version

    async def find_version_by_id(self, version_id):
        return self._version


class _FakeTemporalClient:
    def __init__(self):
        self.started: list = []

    async def start_workflow(self, run_method, payload, *, id, task_queue):
        self.started.append((payload, id, task_queue))


class _FakeDispatcher:
    def __init__(self):
        self.dispatched: list = []

    async def dispatch(self, data):
        self.dispatched.append(data)


def _resolve(
    *,
    case_id: UUID | None = None,
    case_name: str | None = None,
    workflow_repo: _FakeWorkflowRepo | None = None,
    case_repo: _FakeCaseRepo | None = None,
    version: PipelineVersion | None = None,
    client: _FakeTemporalClient | None = None,
    dispatcher: _FakeDispatcher | None = None,
) -> ResolveIngestCase:
    return ResolveIngestCase(
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        case_id=case_id,
        case_name=case_name,
        workflow_repository=workflow_repo or _FakeWorkflowRepo(),
        case_repository=case_repo if case_repo is not None else _FakeCaseRepo(),
        pipeline_repository=_FakePipelineRepo(version or _version()),
        temporal_client=client or _FakeTemporalClient(),
        task_queue="q",
        case_event_dispatcher=dispatcher,
    )


async def test_resolve__no_reference_is_a_clean_noop():
    client, dispatcher, case_repo = _FakeTemporalClient(), _FakeDispatcher(), _FakeCaseRepo()

    result = await _resolve(client=client, dispatcher=dispatcher, case_repo=case_repo).execute()

    expect(result.case).to(be_none)
    expect(result.created).to(be_false)
    expect(case_repo.created).to(be_empty)
    expect(dispatcher.dispatched).to(be_empty)
    expect(client.started).to(be_empty)


async def test_resolve__new_external_ref_creates_case_emits_created_and_starts_case_run():
    client, dispatcher, case_repo = _FakeTemporalClient(), _FakeDispatcher(), _FakeCaseRepo()

    result = await _resolve(
        case_name="EXP-9", client=client, dispatcher=dispatcher, case_repo=case_repo
    ).execute()

    expect(result.created).to(be_true)
    expect(result.case.external_ref).to(equal("EXP-9"))
    expect(result.case.name).to(equal("EXP-9"))
    expect(case_repo.created).to(have_length(1))

    # case.created SOLO en creación real, con la referencia del cliente.
    expect(dispatcher.dispatched).to(have_length(1))
    event = dispatcher.dispatched[0]
    expect(event.event_type).to(equal("case.created"))
    expect(event.case_id).to(equal(result.case.uuid))
    expect(event.error).to(equal({"externalRef": "EXP-9", "name": "EXP-9"}))

    # La receta (binding del workflow) tiene await_documents ⇒ arranca CASE#.
    expect(client.started).to(have_length(1))
    _, run_id, _ = client.started[0]
    expect(run_id).to(equal(f"CASE#{result.case.uuid.hex}"))


async def test_resolve__existing_external_ref_reuses_case_without_duplicate_event():
    existing = _existing_case()
    client, dispatcher = _FakeTemporalClient(), _FakeDispatcher()
    case_repo = _FakeCaseRepo(existing=existing)

    result = await _resolve(
        case_name="EXP-1", client=client, dispatcher=dispatcher, case_repo=case_repo
    ).execute()

    expect(result.created).to(be_false)
    expect(result.case.uuid).to(equal(existing.uuid))
    expect(case_repo.created).to(be_empty)
    expect(dispatcher.dispatched).to(be_empty)
    # EnsureCaseRunStarted corre también al encontrar (idempotente).
    expect(client.started).to(have_length(1))
    _, run_id, _ = client.started[0]
    expect(run_id).to(equal(f"CASE#{existing.uuid.hex}"))


async def test_resolve__creation_race_adopts_existing_case():
    existing = _existing_case()
    client, dispatcher = _FakeTemporalClient(), _FakeDispatcher()
    case_repo = _FakeCaseRepo(existing=existing, race=True)

    result = await _resolve(
        case_name="EXP-1", client=client, dispatcher=dispatcher, case_repo=case_repo
    ).execute()

    expect(result.created).to(be_false)
    expect(result.case.uuid).to(equal(existing.uuid))
    expect(dispatcher.dispatched).to(be_empty)


async def test_resolve__case_id_found_links_without_event():
    existing = _existing_case()
    client, dispatcher = _FakeTemporalClient(), _FakeDispatcher()

    result = await _resolve(
        case_id=existing.uuid,
        client=client,
        dispatcher=dispatcher,
        case_repo=_FakeCaseRepo(existing=existing),
    ).execute()

    expect(result.created).to(be_false)
    expect(result.case.uuid).to(equal(existing.uuid))
    expect(dispatcher.dispatched).to(be_empty)
    expect(client.started).to(have_length(1))


async def test_resolve__unknown_case_id_raises_case_not_found():
    with pytest.raises(IngestCaseNotFoundError):
        await _resolve(case_id=uuid4()).execute()


async def test_resolve__case_id_from_another_workflow_raises_case_not_found():
    foreign = _existing_case(workflow_id=uuid4())

    with pytest.raises(IngestCaseNotFoundError):
        await _resolve(case_id=foreign.uuid, case_repo=_FakeCaseRepo(existing=foreign)).execute()


async def test_resolve__case_reference_rejected_when_workflow_missing():
    # E7 · F2 (caso universal): ya no se exige ANALYSIS — el único rechazo es que
    # el workflow no exista.
    workflow_repo = _FakeWorkflowRepo(missing=True)

    with pytest.raises(IngestCaseNotAllowedError):
        await _resolve(case_name="EXP-1", workflow_repo=workflow_repo).execute()


async def test_resolve__case_run_failure_never_breaks_the_ingest():
    class _BrokenTemporal:
        async def start_workflow(self, *args, **kwargs):
            raise RuntimeError("temporal down")

    dispatcher, case_repo = _FakeDispatcher(), _FakeCaseRepo()

    result = await _resolve(
        case_name="EXP-2", client=_BrokenTemporal(), dispatcher=dispatcher, case_repo=case_repo
    ).execute()

    expect(result.created).to(be_true)
    expect(dispatcher.dispatched).to(have_length(1))
