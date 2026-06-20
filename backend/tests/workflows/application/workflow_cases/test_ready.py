"""E4 · POST …/ready (RequestCaseReady) + EvaluateCaseCompleteness.

No-op si ya ready o sin await_documents; 409 ``case.not_complete`` CON missing
en el contexto cuando faltan docs y no hay force; OK ⇒ asegura el CASE# y
señala ``case_ready {force}``. La completitud persiste snapshot + case_event
``completeness.evaluated`` SOLO si cambió.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from expects import be_empty, be_false, be_true, equal, expect, have_length

from src.common.domain.enums.workflows import WorkflowDocumentStatus
from src.common.domain.exceptions.processing import CaseNotFoundError
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.application.workflow_cases.completeness import EvaluateCaseCompleteness
from src.workflows.application.workflow_cases.ready import (
    CaseNotCompleteError,
    CaseReadySignalError,
    RequestCaseReady,
)
from src.workflows.domain.models.pipeline import PhaseSpec, PipelineVersion
from src.workflows.domain.recipes import standard_case_phases

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")
_PIPELINE = UUID("66666666-6666-6666-6666-666666666666")
_VERSION_ID = UUID("77777777-7777-7777-7777-777777777777")
_TYPE_ANEXO = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _version(*, with_await: bool = True, completeness: dict | None = None) -> PipelineVersion:
    phases = standard_case_phases() if with_await else [{"id": "analyze", "kind": "analyze", "config": {}}]
    # D-A: la completitud va plegada en await_documents.config (required_types +
    # advance), no a nivel-versión. Reflejamos el dict de test en la config de esa fase.
    if completeness is not None:
        cfg: dict = {"required_types": completeness.get("required_types", {})}
        if completeness.get("auto_ready"):
            cfg["advance"] = "auto"
        for phase in phases:
            if phase["kind"] == "await_documents":
                phase["config"] = cfg
                break
    return PipelineVersion(
        uuid=_VERSION_ID,
        pipeline_id=_PIPELINE,
        version=1,
        phases=[PhaseSpec.model_validate(p) for p in phases],
    )


def _case(**overrides) -> WorkflowCase:
    base = dict(
        uuid=uuid4(),
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        name="Case",
        pipeline_version_id=_VERSION_ID,
    )
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


class _FakeDocRepo:
    def __init__(self, documents=None):
        self._documents = documents or []

    async def list_by_case(self, case_id, tenant_id):
        return self._documents


class _FakeDocTypeRepo:
    async def list_by_workflow(self, workflow_id, tenant_id):
        return [SimpleNamespace(uuid=_TYPE_ANEXO, slug="anexo")]


class _FakeEventRepo:
    def __init__(self):
        self.created: list = []

    async def create(self, event):
        self.created.append(event)
        return event


class _FakeHandle:
    def __init__(self, recorder):
        self._recorder = recorder

    async def signal(self, name, *args):
        self._recorder.append((name, args))


class _FakeTemporalClient:
    def __init__(self):
        self.started: list = []
        self.signals: list = []

    async def start_workflow(self, run_method, payload, *, id, task_queue):
        self.started.append((payload, id, task_queue))

    def get_workflow_handle(self, workflow_id):
        return _FakeHandle(self.signals)


def _doc(type_id: UUID) -> WorkflowDocument:
    return WorkflowDocument(
        uuid=uuid4(), tenant_id=_TENANT, document_type_id=type_id, status=WorkflowDocumentStatus.EXTRACTED
    )


def _ready_use_case(case, version, *, documents=None, force=False, client=None):
    return RequestCaseReady(
        tenant_id=_TENANT,
        case_id=case.uuid,
        case_repository=_FakeCaseRepo(case),
        document_repository=_FakeDocRepo(documents),
        document_type_repository=_FakeDocTypeRepo(),
        pipeline_repository=_FakePipelineRepo(version),
        temporal_client=client or _FakeTemporalClient(),
        task_queue="q",
        force=force,
    )


# ─── RequestCaseReady ────────────────────────────────────────────────────────


async def test_ready__noop_when_recipe_has_no_await_documents():
    case = _case()
    result = await _ready_use_case(case, _version(with_await=False)).execute()

    expect(result.outcome).to(equal("no_await_documents"))


async def test_ready__noop_when_already_ready():
    from datetime import UTC, datetime

    case = _case(ready_at=datetime(2026, 6, 10, tzinfo=UTC))
    result = await _ready_use_case(case, _version()).execute()

    expect(result.outcome).to(equal("already_ready"))


async def test_ready__missing_without_force_raises_409_with_missing_detail():
    case = _case()
    version = _version(completeness={"required_types": {"anexo": 1}, "auto_ready": False})

    with pytest.raises(CaseNotCompleteError) as exc_info:
        await _ready_use_case(case, version, documents=[]).execute()

    expect(exc_info.value.status_code).to(equal(409))
    expect(exc_info.value.code).to(equal("case.not_complete"))
    # El FE lee errors[0].missing — viaja en el contexto del DomainError.
    expect(exc_info.value.context["missing"]).to(equal([{"documentType": "anexo", "missing": 1}]))


async def test_ready__force_overrides_missing_and_signals_case_ready():
    case = _case()
    version = _version(completeness={"required_types": {"anexo": 1}, "auto_ready": False})
    client = _FakeTemporalClient()

    result = await _ready_use_case(case, version, documents=[], force=True, client=client).execute()

    expect(result.outcome).to(equal("signaled"))
    expect(client.signals).to(have_length(1))
    name, args = client.signals[0]
    expect(name).to(equal("case_ready"))
    expect(args).to(equal(({"force": True},)))


async def test_ready__satisfied_signals_without_force():
    case = _case()
    version = _version(completeness={"required_types": {"anexo": 1}, "auto_ready": False})
    client = _FakeTemporalClient()

    result = await _ready_use_case(
        case, version, documents=[_doc(_TYPE_ANEXO)], client=client
    ).execute()

    expect(result.outcome).to(equal("signaled"))
    name, args = client.signals[0]
    expect(name).to(equal("case_ready"))
    expect(args).to(equal(({"force": False},)))


# ─── EvaluateCaseCompleteness (persistencia + evento solo si cambió) ─────────


def _completeness_use_case(case, version, documents, event_repo, case_repo=None):
    return EvaluateCaseCompleteness(
        tenant_id=_TENANT,
        case_id=case.uuid,
        case_repository=case_repo or _FakeCaseRepo(case),
        document_repository=_FakeDocRepo(documents),
        document_type_repository=_FakeDocTypeRepo(),
        pipeline_repository=_FakePipelineRepo(version),
        case_event_repository=event_repo,
        persist=True,
    )


async def test_completeness__persists_snapshot_and_appends_event_when_changed():
    case = _case(completeness=None)
    case_repo = _FakeCaseRepo(case)
    event_repo = _FakeEventRepo()
    version = _version(completeness={"required_types": {"anexo": 1}, "auto_ready": False})

    result = await _completeness_use_case(
        case, version, [_doc(_TYPE_ANEXO)], event_repo, case_repo
    ).execute()

    expect(result.satisfied).to(be_true)
    expect(result.changed).to(be_true)
    expect(case_repo.updated).to(have_length(1))
    expect(case_repo.updated[0].completeness).to(equal(result.snapshot))
    expect(event_repo.created).to(have_length(1))
    expect(event_repo.created[0].type).to(equal("completeness.evaluated"))
    expect(event_repo.created[0].payload).to(equal(result.snapshot))


async def test_completeness__no_event_when_snapshot_unchanged():
    snapshot = {
        "satisfied": False,
        "required": {"anexo": 1},
        "present": {},
        "missing": [{"documentType": "anexo", "missing": 1}],
    }
    case = _case(completeness=snapshot)
    case_repo = _FakeCaseRepo(case)
    event_repo = _FakeEventRepo()
    version = _version(completeness={"required_types": {"anexo": 1}, "auto_ready": False})

    result = await _completeness_use_case(case, version, [], event_repo, case_repo).execute()

    expect(result.changed).to(be_false)
    expect(case_repo.updated).to(be_empty)
    expect(event_repo.created).to(be_empty)


# ─── Fixes del review adversarial E4 ─────────────────────────────────────────


async def test_ready__case_of_another_workflow_is_not_found():
    # El workflow del path DEBE coincidir con el del caso (espejo de
    # ResolveIngestCase): sin esto, un miembro de W2 mutaba casos de W1.
    case = _case()
    use_case = _ready_use_case(case, _version())
    use_case.workflow_id = uuid4()

    with pytest.raises(CaseNotFoundError):
        await use_case.execute()


async def test_ready__signal_failure_raises_503_instead_of_silent_success():
    class _BrokenHandle:
        async def signal(self, name, *args):
            raise RuntimeError("temporal down")

    class _BrokenSignalClient(_FakeTemporalClient):
        def get_workflow_handle(self, workflow_id):
            return _BrokenHandle()

    case = _case()
    use_case = _ready_use_case(
        case,
        _version(completeness={"required_types": {"anexo": 1}, "auto_ready": False}),
        documents=[_doc(_TYPE_ANEXO)],
        client=_BrokenSignalClient(),
    )

    with pytest.raises(CaseReadySignalError):
        await use_case.execute()
