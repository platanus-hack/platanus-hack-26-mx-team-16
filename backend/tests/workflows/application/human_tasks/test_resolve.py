"""F6: resolving a HumanTask persists the resolution and signals the run."""

from uuid import UUID, uuid4

import pytest
from expects import be_none, contain, equal, expect, have_length

from src.common.domain.enums.human_tasks import HumanTaskKind, HumanTaskStatus
from src.workflows.application.human_tasks.resolve import (
    QA_FAILED_EVENT,
    QA_PASSED_EVENT,
    TASK_RESOLVED_SIGNAL,
    HumanTaskClaimConflictError,
    HumanTaskNotAnApproverError,
    HumanTaskOpenFlagsError,
    HumanTaskSignalError,
    ResolveHumanTask,
)
from src.workflows.domain.models.human_task import HumanTask

_TENANT = UUID("22222222-2222-2222-2222-222222222222")


def _task(status: HumanTaskStatus, resolution: dict | None = None) -> HumanTask:
    return HumanTask(
        uuid=uuid4(),
        tenant_id=_TENANT,
        task_key="run-1:review1",
        kind=HumanTaskKind.APPROVAL,
        status=status,
        pipeline_run_id="run-1",
        resolution=resolution,
    )


class _FakeRepo:
    def __init__(self, task):
        self._task = task
        self.resolved_with = None

    async def find_by_id(self, task_id, tenant_id):
        return self._task

    async def resolve(self, task_id, tenant_id, resolution):
        self.resolved_with = resolution
        return self._task.model_copy(update={"status": HumanTaskStatus.RESOLVED, "resolution": resolution})


class _FakeHandle:
    """Espejo de la firma REAL del cliente temporalio: señales multi-arg van
    por el kwarg ``args=[...]`` — posicionales extra lanzan TypeError (el bug
    que este fake enmascaraba hasta E4)."""

    def __init__(self):
        self.signals = []

    async def signal(self, name, *, args):
        self.signals.append((name, list(args)))


class _FakeClient:
    def __init__(self, handle):
        self._handle = handle

    def get_workflow_handle(self, run_id):
        return self._handle


async def test_resolve__persists_and_signals_run():
    repo = _FakeRepo(_task(HumanTaskStatus.PENDING))
    handle = _FakeHandle()

    await ResolveHumanTask(
        task_id=uuid4(),
        tenant_id=_TENANT,
        resolution={"approved": True},
        repository=repo,
        temporal_client=_FakeClient(handle),
    ).execute()

    expect(repo.resolved_with).to(equal({"approved": True}))
    expect(handle.signals).to(contain((TASK_RESOLVED_SIGNAL, ["run-1:review1", {"approved": True}])))


async def test_resolve__skips_already_resolved_task():
    repo = _FakeRepo(_task(HumanTaskStatus.RESOLVED))
    handle = _FakeHandle()

    await ResolveHumanTask(
        task_id=uuid4(),
        tenant_id=_TENANT,
        resolution={"approved": True},
        repository=repo,
        temporal_client=_FakeClient(handle),
    ).execute()

    expect(repo.resolved_with).to(equal(None))
    expect(handle.signals).to(equal([]))


async def test_resolve__retry_on_resolved_task_resignals_best_effort():
    # Fix E4: si la señal del primer resolve falló (run quedó esperando con la
    # fila ya resuelta), reintentar el resolve re-señala — auto-sanador.
    repo = _FakeRepo(_task(HumanTaskStatus.RESOLVED, resolution={"approved": True}))
    handle = _FakeHandle()

    await ResolveHumanTask(
        task_id=uuid4(),
        tenant_id=_TENANT,
        resolution={"approved": True},
        repository=repo,
        temporal_client=_FakeClient(handle),
    ).execute()

    expect(repo.resolved_with).to(equal(None))  # no re-persiste
    expect(handle.signals).to(contain((TASK_RESOLVED_SIGNAL, ["run-1:review1", {"approved": True}])))


async def test_resolve__signal_failure_raises_503_after_persisting():
    class _BrokenHandle:
        async def signal(self, name, *, args):
            raise RuntimeError("temporal down")

    repo = _FakeRepo(_task(HumanTaskStatus.PENDING))

    with pytest.raises(HumanTaskSignalError):
        await ResolveHumanTask(
            task_id=uuid4(),
            tenant_id=_TENANT,
            resolution={"approved": True},
            repository=repo,
            temporal_client=_FakeClient(_BrokenHandle()),
        ).execute()

    # La resolución SÍ quedó persistida — el retry entra por la rama resolved.
    expect(repo.resolved_with).to(equal({"approved": True}))


# ─── E5 §3.2: claim/holder ───────────────────────────────────────────────────


async def test_resolve__claimed_by_other_actor_raises_409_with_holder():
    task = _task(HumanTaskStatus.PENDING).model_copy(update={"claimed_by": "user:other"})
    repo = _FakeRepo(task)
    handle = _FakeHandle()

    with pytest.raises(HumanTaskClaimConflictError) as exc_info:
        await ResolveHumanTask(
            task_id=uuid4(),
            tenant_id=_TENANT,
            resolution={"approved": True},
            repository=repo,
            temporal_client=_FakeClient(handle),
            actor="user:me",
        ).execute()

    expect(exc_info.value.context["holder"]).to(equal("user:other"))
    expect(repo.resolved_with).to(equal(None))
    expect(handle.signals).to(equal([]))


async def test_resolve__actor_is_recorded_in_resolution():
    repo = _FakeRepo(_task(HumanTaskStatus.PENDING))
    handle = _FakeHandle()

    await ResolveHumanTask(
        task_id=uuid4(),
        tenant_id=_TENANT,
        resolution={"approved": True},
        repository=repo,
        temporal_client=_FakeClient(handle),
        actor="staff:s1",
    ).execute()

    expect(repo.resolved_with).to(equal({"approved": True, "resolvedBy": "staff:s1"}))


# ─── E5 §3.4: invariante open_flags ──────────────────────────────────────────


class _FakeDoc:
    def __init__(self, uuid, needs=None, verification=None):
        self.uuid = uuid
        self.needs_clarification = needs
        self.verification = verification


class _FakeDocRepo:
    def __init__(self, documents):
        self._documents = documents

    async def list_by_case(self, case_id, tenant_id):
        return self._documents


def _approval_with_case(items: list | None = None) -> HumanTask:
    return _task(HumanTaskStatus.PENDING).model_copy(update={"case_id": uuid4(), "payload": {"items": items or []}})


async def test_resolve__approve_with_open_flags_raises_409_with_field_list():
    doc_id = uuid4()
    task = _approval_with_case()
    repo = _FakeRepo(task)
    doc_repo = _FakeDocRepo([_FakeDoc(doc_id, needs=["total", "nit"], verification={"nit": {"level": 1}})])

    with pytest.raises(HumanTaskOpenFlagsError) as exc_info:
        await ResolveHumanTask(
            task_id=uuid4(),
            tenant_id=_TENANT,
            resolution={"approved": True},
            repository=repo,
            temporal_client=_FakeClient(_FakeHandle()),
            actor="user:me",
            document_repository=doc_repo,
        ).execute()

    expect(exc_info.value.status_code).to(equal(409))
    expect(exc_info.value.code).to(equal("human_task.open_flags"))
    # Solo `total` sigue abierto: `nit` ya tiene entrada en verification.
    expect(exc_info.value.context["openFields"]).to(equal([{"documentId": str(doc_id), "fieldPath": "total"}]))
    expect(repo.resolved_with).to(equal(None))


async def test_resolve__open_flags_includes_stage_gate_items_from_payload():
    doc_id = uuid4()
    task = _approval_with_case(items=[{"documentId": str(doc_id), "fieldPath": "monto"}])
    repo = _FakeRepo(task)
    doc_repo = _FakeDocRepo([_FakeDoc(doc_id, needs=[], verification={})])

    with pytest.raises(HumanTaskOpenFlagsError) as exc_info:
        await ResolveHumanTask(
            task_id=uuid4(),
            tenant_id=_TENANT,
            resolution={"approved": True},
            repository=repo,
            temporal_client=_FakeClient(_FakeHandle()),
            document_repository=doc_repo,
        ).execute()

    expect(exc_info.value.context["openFields"]).to(equal([{"documentId": str(doc_id), "fieldPath": "monto"}]))


async def test_resolve__force_true_skips_open_flags_invariant():
    doc_id = uuid4()
    repo = _FakeRepo(_approval_with_case())
    doc_repo = _FakeDocRepo([_FakeDoc(doc_id, needs=["total"], verification={})])
    handle = _FakeHandle()

    await ResolveHumanTask(
        task_id=uuid4(),
        tenant_id=_TENANT,
        resolution={"approved": True, "force": True},
        repository=repo,
        temporal_client=_FakeClient(handle),
        document_repository=doc_repo,
    ).execute()

    expect(repo.resolved_with).to(equal({"approved": True, "force": True}))


async def test_resolve__reject_never_checks_open_flags():
    doc_id = uuid4()
    repo = _FakeRepo(_approval_with_case())
    doc_repo = _FakeDocRepo([_FakeDoc(doc_id, needs=["total"], verification={})])

    await ResolveHumanTask(
        task_id=uuid4(),
        tenant_id=_TENANT,
        resolution={"approved": False},
        repository=repo,
        temporal_client=_FakeClient(_FakeHandle()),
        document_repository=doc_repo,
    ).execute()

    expect(repo.resolved_with).to(equal({"approved": False}))


async def test_resolve__verified_flags_allow_approval():
    doc_id = uuid4()
    repo = _FakeRepo(_approval_with_case())
    doc_repo = _FakeDocRepo([_FakeDoc(doc_id, needs=["total"], verification={"total": {"level": 2}})])

    await ResolveHumanTask(
        task_id=uuid4(),
        tenant_id=_TENANT,
        resolution={"approved": True},
        repository=repo,
        temporal_client=_FakeClient(_FakeHandle()),
        document_repository=doc_repo,
    ).execute()

    expect(repo.resolved_with).to(equal({"approved": True}))


async def test_resolve__external_level0_does_not_satisfy_open_flags():
    # Minor: una corrección external (level 0) NO cuenta como verificación que
    # habilite approve sin force — exige level>=1 del stage (o force).
    doc_id = uuid4()
    repo = _FakeRepo(_approval_with_case())
    doc_repo = _FakeDocRepo([_FakeDoc(doc_id, needs=["total"], verification={"total": {"level": 0}})])

    with pytest.raises(HumanTaskOpenFlagsError) as exc_info:
        await ResolveHumanTask(
            task_id=uuid4(),
            tenant_id=_TENANT,
            resolution={"approved": True},
            repository=repo,
            temporal_client=_FakeClient(_FakeHandle()),
            document_repository=doc_repo,
        ).execute()

    expect(exc_info.value.context["openFields"]).to(equal([{"documentId": str(doc_id), "fieldPath": "total"}]))
    expect(repo.resolved_with).to(equal(None))


# ─── E5 §C5: carrera perdida en el UPDATE condicional ────────────────────────


class _RaceLostRepo:
    """Simula la rama 0-filas del repo: el caller pasa el check inicial
    (pending) pero, cuando llama a ``resolve``, otro resolve ya ganó — el repo
    devuelve la fila YA resuelta con la resolución del GANADOR, no la nuestra."""

    def __init__(self, pending_task, stored_resolution):
        self._pending = pending_task
        self._stored = stored_resolution
        self.resolved_with = None

    async def find_by_id(self, task_id, tenant_id):
        return self._pending

    async def resolve(self, task_id, tenant_id, resolution):
        self.resolved_with = resolution
        return self._pending.model_copy(update={"status": HumanTaskStatus.RESOLVED, "resolution": self._stored})


async def test_resolve__race_lost_resignals_stored_resolution_not_ours():
    # El ganador aprobó; nuestro resolve (rechazo) llega tarde ⇒ NO sobrescribe
    # y re-señala la resolución ALMACENADA del ganador (idempotente).
    pending = _task(HumanTaskStatus.PENDING)
    repo = _RaceLostRepo(pending, stored_resolution={"approved": True, "resolvedBy": "user:winner"})
    handle = _FakeHandle()

    result = await ResolveHumanTask(
        task_id=uuid4(),
        tenant_id=_TENANT,
        resolution={"approved": False},
        repository=repo,
        temporal_client=_FakeClient(handle),
        actor="user:loser",
    ).execute()

    expect(result.resolution).to(equal({"approved": True, "resolvedBy": "user:winner"}))
    expect(handle.signals).to(
        contain((TASK_RESOLVED_SIGNAL, ["run-1:review1", {"approved": True, "resolvedBy": "user:winner"}]))
    )


async def test_resolve__retry_resignal_failure_raises_503():
    # Minor: en la rama "ya resuelta" (retry), si el re-signal best-effort vuelve
    # a fallar ⇒ propagar 503 (no 200 con el run pausado para siempre).
    class _BrokenHandle:
        async def signal(self, name, *, args):
            raise RuntimeError("temporal still down")

    repo = _FakeRepo(_task(HumanTaskStatus.RESOLVED, resolution={"approved": True}))

    with pytest.raises(HumanTaskSignalError):
        await ResolveHumanTask(
            task_id=uuid4(),
            tenant_id=_TENANT,
            resolution={"approved": True},
            repository=repo,
            temporal_client=_FakeClient(_BrokenHandle()),
        ).execute()

    expect(repo.resolved_with).to(equal(None))  # no re-persiste en el retry


# ─── E6 §3: resolución de tareas QA (fire-and-forget, sin run pausado) ─────────


class _FakeCaseEventRepo:
    def __init__(self):
        self.created = []

    async def create(self, event):
        self.created.append(event)
        return event

    async def list_by_case(self, *a, **k):  # pragma: no cover — no usado aquí
        return []

    async def count_by_type_since(self, *a, **k):  # pragma: no cover
        return []


def _qa_task() -> HumanTask:
    return HumanTask(
        uuid=uuid4(),
        tenant_id=_TENANT,
        task_key="run-1:qa",
        kind=HumanTaskKind.QA,
        status=HumanTaskStatus.PENDING,
        case_id=uuid4(),
        # CRÍTICO: una task QA NO tiene run pausado.
        pipeline_run_id=None,
    )


async def test_resolve__qa_pass_writes_qa_passed_event_and_never_signals():
    task = _qa_task()
    repo = _FakeRepo(task)
    handle = _FakeHandle()
    events = _FakeCaseEventRepo()

    await ResolveHumanTask(
        task_id=task.uuid,
        tenant_id=_TENANT,
        resolution={"passed": True},
        repository=repo,
        temporal_client=_FakeClient(handle),
        actor="staff:s1",
        case_event_repository=events,
    ).execute()

    # NO se señala Temporal (pipeline_run_id None).
    expect(handle.signals).to(equal([]))
    # Se registró el veredicto qa.passed con el actor.
    expect(len(events.created)).to(equal(1))
    event = events.created[0]
    expect(event.type).to(equal(QA_PASSED_EVENT))
    expect(event.case_id).to(equal(task.case_id))
    expect(event.actor).to(equal("staff:s1"))
    expect(event.payload).to(equal({"taskId": str(task.uuid)}))


async def test_resolve__qa_fail_writes_qa_failed_event_with_findings():
    task = _qa_task()
    repo = _FakeRepo(task)
    events = _FakeCaseEventRepo()

    await ResolveHumanTask(
        task_id=task.uuid,
        tenant_id=_TENANT,
        resolution={"passed": False, "findings": "total mal extraído"},
        repository=repo,
        temporal_client=_FakeClient(_FakeHandle()),
        case_event_repository=events,
    ).execute()

    expect(events.created[0].type).to(equal(QA_FAILED_EVENT))
    expect(events.created[0].payload).to(equal({"taskId": str(task.uuid), "findings": "total mal extraído"}))


async def test_resolve__qa_without_event_repo_is_noop_but_still_resolves():
    # Compat: sin case_event_repository la task QA se resuelve sin registrar.
    task = _qa_task()
    repo = _FakeRepo(task)
    handle = _FakeHandle()

    resolved = await ResolveHumanTask(
        task_id=task.uuid,
        tenant_id=_TENANT,
        resolution={"passed": True},
        repository=repo,
        temporal_client=_FakeClient(handle),
    ).execute()

    expect(resolved.status).to(equal(HumanTaskStatus.RESOLVED))
    expect(handle.signals).to(equal([]))


async def test_resolve__non_qa_task_does_not_write_qa_events():
    # Un APPROVAL normal jamás escribe qa.* aunque haya case_event_repository.
    repo = _FakeRepo(_task(HumanTaskStatus.PENDING))
    events = _FakeCaseEventRepo()

    await ResolveHumanTask(
        task_id=uuid4(),
        tenant_id=_TENANT,
        resolution={"approved": True},
        repository=repo,
        temporal_client=_FakeClient(_FakeHandle()),
        case_event_repository=events,
    ).execute()

    expect(events.created).to(equal([]))


# ── F4 · quórum N-de-M (acumulación de votos en el endpoint) ─────────────────


class _QuorumRepo:
    def __init__(self, task):
        self._task = task
        self.resolved_with = None

    async def find_by_id(self, task_id, tenant_id):
        return self._task

    async def upsert(self, task):
        self._task = task
        return task

    async def resolve(self, task_id, tenant_id, resolution):
        self.resolved_with = resolution
        self._task = self._task.model_copy(update={"status": HumanTaskStatus.RESOLVED, "resolution": resolution})
        return self._task


def _quorum_task() -> HumanTask:
    return HumanTask(
        uuid=uuid4(),
        tenant_id=_TENANT,
        task_key="run-1:approval",
        kind=HumanTaskKind.APPROVAL,
        status=HumanTaskStatus.PENDING,
        pipeline_run_id="run-1",
        payload={
            "approvalsRequired": 2,
            "distinctApprovers": True,
            "approvers": {"users": ["u1", "u2", "u3"]},
        },
    )


async def test_quorum_resolve__first_vote_keeps_pending_and_signals():
    repo = _QuorumRepo(_quorum_task())
    handle = _FakeHandle()

    result = await ResolveHumanTask(
        task_id=repo._task.uuid,
        tenant_id=_TENANT,
        resolution={"approved": True},
        repository=repo,
        temporal_client=_FakeClient(handle),
        actor="user:u1",
    ).execute()

    expect(result.status).to(equal(HumanTaskStatus.PENDING))  # aún falta 1 voto
    expect(repo.resolved_with).to(be_none)
    expect(handle.signals).to(have_length(1))  # el voto se señaló al run
    expect(repo._task.payload["votes"]).to(have_length(1))


async def test_quorum_resolve__second_distinct_vote_reaches_quorum():
    repo = _QuorumRepo(_quorum_task())
    task_id = repo._task.uuid
    base = dict(task_id=task_id, tenant_id=_TENANT, resolution={"approved": True}, repository=repo)
    await ResolveHumanTask(**base, temporal_client=_FakeClient(_FakeHandle()), actor="user:u1").execute()
    result = await ResolveHumanTask(**base, temporal_client=_FakeClient(_FakeHandle()), actor="user:u2").execute()

    expect(result.status).to(equal(HumanTaskStatus.RESOLVED))
    expect(repo.resolved_with["approved"]).to(equal(True))


async def test_quorum_resolve__non_approver_is_403():
    repo = _QuorumRepo(_quorum_task())

    with pytest.raises(HumanTaskNotAnApproverError):
        await ResolveHumanTask(
            task_id=repo._task.uuid,
            tenant_id=_TENANT,
            resolution={"approved": True},
            repository=repo,
            temporal_client=_FakeClient(_FakeHandle()),
            actor="user:stranger",
        ).execute()
