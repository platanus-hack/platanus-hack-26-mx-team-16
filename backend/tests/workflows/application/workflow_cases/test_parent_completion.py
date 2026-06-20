"""E5 · diseño §2.2: auto-cierre del padre en el choke point TransitionCaseStatus.

Un child con ``parent_case_id`` que entra a estado terminal dispara
``maybe_complete_parent``: 0 hermanos no-terminales ⇒ padre PROCESSING→COMPLETED
+ case_event ``children.completed`` ({total, byStatus}, dedupe). La carrera
entre los dos últimos hermanos es benigna (no-op + dedupe).
"""

from __future__ import annotations

from uuid import UUID, uuid4

from expects import be_false, be_true, equal, expect, have_length

from src.common.domain.enums.workflow_cases import WorkflowCaseStatus
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.workflows.application.workflow_cases.transition import (
    CHILDREN_COMPLETED_EVENT,
    CHILDREN_COMPLETED_RECOVERY_REASON,
    STATUS_CHANGED_EVENT,
    TransitionCaseStatus,
    maybe_complete_parent,
)

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")


def _case(status: WorkflowCaseStatus, parent_case_id: UUID | None = None) -> WorkflowCase:
    return WorkflowCase(
        uuid=uuid4(),
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        name="Case",
        status=status,
        parent_case_id=parent_case_id,
    )


class _FakeCaseRepo:
    """Repo en memoria con conteo real de children por status."""

    def __init__(self, cases: list[WorkflowCase]):
        self._cases = {case.uuid: case for case in cases}
        self.updates: list[WorkflowCase] = []

    async def find_by_id(self, case_id, tenant_id):
        return self._cases.get(case_id)

    async def update(self, case):
        self._cases[case.uuid] = case
        self.updates.append(case)
        return case

    async def count_children_by_status(self, parent_case_id, tenant_id):
        counts: dict[str, int] = {}
        for case in self._cases.values():
            if case.parent_case_id == parent_case_id:
                counts[case.status.value] = counts.get(case.status.value, 0) + 1
        return counts


class _FakeEventRepo:
    """Honra el unique de ``dedupe_key`` como el SQLCaseEventRepository real."""

    def __init__(self):
        self.created = []

    async def create(self, event):
        if event.dedupe_key is not None:
            for existing in self.created:
                if existing.dedupe_key == event.dedupe_key:
                    return existing
        self.created.append(event)
        return event


def _transition(case_repo, event_repo, case_id, to_status) -> TransitionCaseStatus:
    return TransitionCaseStatus(
        tenant_id=_TENANT,
        case_id=case_id,
        to_status=to_status,
        case_repository=case_repo,
        case_event_repository=event_repo,
        actor="system",
    )


async def test_last_terminal_child_completes_parent_with_breakdown_event():
    parent = _case(WorkflowCaseStatus.PROCESSING)
    sibling = _case(WorkflowCaseStatus.COMPLETED, parent_case_id=parent.uuid)
    rejected = _case(WorkflowCaseStatus.REJECTED, parent_case_id=parent.uuid)
    last = _case(WorkflowCaseStatus.REVIEW_L2, parent_case_id=parent.uuid)
    case_repo = _FakeCaseRepo([parent, sibling, rejected, last])
    event_repo = _FakeEventRepo()

    await _transition(case_repo, event_repo, last.uuid, WorkflowCaseStatus.COMPLETED).execute()

    expect(case_repo._cases[parent.uuid].status).to(equal(WorkflowCaseStatus.COMPLETED))
    children_events = [e for e in event_repo.created if e.type == CHILDREN_COMPLETED_EVENT]
    expect(children_events).to(have_length(1))
    event = children_events[0]
    expect(event.case_id).to(equal(parent.uuid))
    expect(event.payload).to(
        equal({"total": 3, "byStatus": {"COMPLETED": 2, "REJECTED": 1}})
    )
    expect(event.dedupe_key).to(equal(f"parent:{parent.uuid}:{CHILDREN_COMPLETED_EVENT}"))
    # status.changed del child + status.changed del padre.
    status_events = [e for e in event_repo.created if e.type == STATUS_CHANGED_EVENT]
    expect(status_events).to(have_length(2))


async def test_pending_sibling_keeps_parent_processing():
    parent = _case(WorkflowCaseStatus.PROCESSING)
    pending = _case(WorkflowCaseStatus.ANALYZING, parent_case_id=parent.uuid)
    last = _case(WorkflowCaseStatus.REVIEW_L2, parent_case_id=parent.uuid)
    case_repo = _FakeCaseRepo([parent, pending, last])
    event_repo = _FakeEventRepo()

    await _transition(case_repo, event_repo, last.uuid, WorkflowCaseStatus.COMPLETED).execute()

    expect(case_repo._cases[parent.uuid].status).to(equal(WorkflowCaseStatus.PROCESSING))
    expect([e for e in event_repo.created if e.type == CHILDREN_COMPLETED_EVENT]).to(equal([]))


async def test_non_terminal_child_transition_does_not_touch_parent():
    parent = _case(WorkflowCaseStatus.PROCESSING)
    child = _case(WorkflowCaseStatus.PROCESSING, parent_case_id=parent.uuid)
    case_repo = _FakeCaseRepo([parent, child])
    event_repo = _FakeEventRepo()

    await _transition(case_repo, event_repo, child.uuid, WorkflowCaseStatus.ANALYZING).execute()

    expect(case_repo._cases[parent.uuid].status).to(equal(WorkflowCaseStatus.PROCESSING))
    expect([e for e in event_repo.created if e.type == CHILDREN_COMPLETED_EVENT]).to(equal([]))


async def test_concurrent_last_siblings_race_is_noop_and_dedupes_event():
    # Carrera: los dos últimos hermanos terminan "a la vez" — la segunda
    # evaluación ve al padre ya COMPLETED (no-op legal) y el dedupe absorbe
    # el evento doble.
    parent = _case(WorkflowCaseStatus.PROCESSING)
    a = _case(WorkflowCaseStatus.COMPLETED, parent_case_id=parent.uuid)
    b = _case(WorkflowCaseStatus.COMPLETED, parent_case_id=parent.uuid)
    case_repo = _FakeCaseRepo([parent, a, b])
    event_repo = _FakeEventRepo()

    first = await maybe_complete_parent(
        tenant_id=_TENANT,
        parent_case_id=parent.uuid,
        case_repository=case_repo,
        case_event_repository=event_repo,
    )
    second = await maybe_complete_parent(
        tenant_id=_TENANT,
        parent_case_id=parent.uuid,
        case_repository=case_repo,
        case_event_repository=event_repo,
    )

    expect(first).to(be_true)
    expect(second).to(be_true)
    expect(case_repo._cases[parent.uuid].status).to(equal(WorkflowCaseStatus.COMPLETED))
    children_events = [e for e in event_repo.created if e.type == CHILDREN_COMPLETED_EVENT]
    expect(children_events).to(have_length(1))  # dedupe absorbió el doble
    status_events = [e for e in event_repo.created if e.type == STATUS_CHANGED_EVENT]
    expect(status_events).to(have_length(1))  # una sola transición real del padre


async def test_maybe_complete_parent__without_children_is_noop():
    parent = _case(WorkflowCaseStatus.PROCESSING)
    case_repo = _FakeCaseRepo([parent])
    event_repo = _FakeEventRepo()

    result = await maybe_complete_parent(
        tenant_id=_TENANT,
        parent_case_id=parent.uuid,
        case_repository=case_repo,
        case_event_repository=event_repo,
    )

    expect(result).to(be_false)
    expect(event_repo.created).to(equal([]))


async def test_maybe_complete_parent__receiving_parent_recovers_and_completes():
    # C3: la señal ``case_split`` se perdió ⇒ el padre quedó RECEIVING mientras
    # todos sus children terminaban. RECEIVING→COMPLETED es ilegal, pero el
    # auto-cierre recupera el limbo (RECEIVING→PROCESSING→COMPLETED) en vez de
    # dejar al padre varado para siempre.
    parent = _case(WorkflowCaseStatus.RECEIVING)
    child = _case(WorkflowCaseStatus.COMPLETED, parent_case_id=parent.uuid)
    case_repo = _FakeCaseRepo([parent, child])
    event_repo = _FakeEventRepo()

    result = await maybe_complete_parent(
        tenant_id=_TENANT,
        parent_case_id=parent.uuid,
        case_repository=case_repo,
        case_event_repository=event_repo,
    )

    expect(result).to(be_true)
    expect(case_repo._cases[parent.uuid].status).to(equal(WorkflowCaseStatus.COMPLETED))
    # Rastro de la recuperación: una transición RECEIVING→PROCESSING con su reason.
    recovery_events = [
        e
        for e in event_repo.created
        if e.type == STATUS_CHANGED_EVENT
        and e.payload.get("reason") == CHILDREN_COMPLETED_RECOVERY_REASON
    ]
    expect(recovery_events).to(have_length(1))
    expect(recovery_events[0].payload).to(
        equal(
            {
                "from": WorkflowCaseStatus.RECEIVING.value,
                "to": WorkflowCaseStatus.PROCESSING.value,
                "reason": CHILDREN_COMPLETED_RECOVERY_REASON,
            }
        )
    )
    # El desglose final se appendea igual.
    children_events = [e for e in event_repo.created if e.type == CHILDREN_COMPLETED_EVENT]
    expect(children_events).to(have_length(1))
