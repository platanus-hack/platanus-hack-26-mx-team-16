"""E5 · W4: ClaimL1Task / ResolveL1Task — lock pesimista y resolve con actor staff."""

from uuid import UUID, uuid4

import pytest
from expects import be_none, equal, expect

from src.common.domain.enums.human_tasks import HumanTaskKind, HumanTaskStatus
from src.staff.application.claim import ClaimL1Task, staff_actor
from src.staff.application.resolve import ResolveL1Task
from src.staff.domain.exceptions import (
    StaffTaskClaimConflictError,
    StaffTaskNotClaimableError,
    StaffTaskNotFoundError,
)
from src.staff.domain.models.staff_user import StaffRole, StaffUser
from src.workflows.application.human_tasks.resolve import TASK_RESOLVED_SIGNAL
from src.workflows.domain.models.human_task import HumanTask

_TENANT = UUID("33333333-3333-3333-3333-333333333333")


def _staff(role: StaffRole = StaffRole.STAFF_ANALYST_L1) -> StaffUser:
    return StaffUser(uuid=uuid4(), user_id=uuid4(), role=role)


def _task(**overrides) -> HumanTask:
    defaults = dict(
        uuid=uuid4(),
        tenant_id=_TENANT,
        task_key="run-9:human_review:review_l1",
        kind=HumanTaskKind.APPROVAL,
        status=HumanTaskStatus.PENDING,
        stage="review_l1",
        pipeline_run_id="run-9",
    )
    defaults.update(overrides)
    return HumanTask(**defaults)


class _FakeStaffTaskRepo:
    def __init__(self, task: HumanTask | None, claim_result: HumanTask | None = None):
        self._task = task
        self._claim_result = claim_result
        self.claimed_with: tuple | None = None
        self.released_with: tuple | None = None

    async def find_by_id(self, task_id):
        return self._task

    async def claim(self, task_id, actor):
        self.claimed_with = (task_id, actor)
        return self._claim_result

    async def release(self, task_id, actor, force=False):
        self.released_with = (task_id, actor, force)
        return self._claim_result


class _FakeHumanTaskRepo:
    def __init__(self, task: HumanTask):
        self._task = task
        self.resolved_with: dict | None = None

    async def find_by_id(self, task_id, tenant_id):
        assert tenant_id == self._task.tenant_id  # el tenant sale de la fila
        return self._task

    async def resolve(self, task_id, tenant_id, resolution):
        self.resolved_with = resolution
        return self._task.model_copy(
            update={"status": HumanTaskStatus.RESOLVED, "resolution": resolution}
        )


class _FakeHandle:
    def __init__(self):
        self.signals = []

    async def signal(self, name, *, args):
        self.signals.append((name, list(args)))


class _FakeClient:
    def __init__(self, handle):
        self._handle = handle

    def get_workflow_handle(self, run_id):
        return self._handle


async def test_claim__translates_zero_rows_into_conflict_with_holder():
    holder = f"staff:{uuid4()}"
    task = _task(claimed_by=holder)
    repo = _FakeStaffTaskRepo(task, claim_result=None)

    try:
        await ClaimL1Task(task_id=task.uuid, staff_user=_staff(), repository=repo).execute()
        raise AssertionError("expected StaffTaskClaimConflictError")
    except StaffTaskClaimConflictError as error:
        expect(error.status_code).to(equal(409))
        expect(error.code).to(equal("human_task.already_claimed"))
        expect(error.context["holder"]).to(equal(holder))


async def test_claim__missing_task_is_404():
    repo = _FakeStaffTaskRepo(task=None, claim_result=None)
    with pytest.raises(StaffTaskNotFoundError):
        await ClaimL1Task(task_id=uuid4(), staff_user=_staff(), repository=repo).execute()


async def test_claim__non_pending_unclaimed_task_is_not_claimable():
    task = _task(status=HumanTaskStatus.RESOLVED)
    repo = _FakeStaffTaskRepo(task, claim_result=None)
    with pytest.raises(StaffTaskNotClaimableError):
        await ClaimL1Task(task_id=task.uuid, staff_user=_staff(), repository=repo).execute()


async def test_release__forces_only_for_staff_admin():
    task = _task(claimed_by="staff:someone-else")
    admin = _staff(role=StaffRole.STAFF_ADMIN)
    repo = _FakeStaffTaskRepo(task, claim_result=task.model_copy(update={"claimed_by": None}))

    await ClaimL1Task(
        task_id=task.uuid, staff_user=admin, repository=repo, release=True
    ).execute()

    expect(repo.released_with[2]).to(equal(True))  # force=True para admin

    analyst = _staff()
    await ClaimL1Task(
        task_id=task.uuid, staff_user=analyst, repository=repo, release=True
    ).execute()
    expect(repo.released_with[2]).to(equal(False))


async def test_resolve_l1__auto_claims_resolves_and_signals_with_staff_actor():
    staff = _staff()
    actor = staff_actor(staff)
    task = _task()
    staff_repo = _FakeStaffTaskRepo(task, claim_result=task.model_copy(update={"claimed_by": actor}))
    human_repo = _FakeHumanTaskRepo(task)
    handle = _FakeHandle()

    resolved = await ResolveL1Task(
        task_id=task.uuid,
        staff_user=staff,
        resolution={"approved": True},
        staff_task_repository=staff_repo,
        human_task_repository=human_repo,
        temporal_client=_FakeClient(handle),
    ).execute()

    expect(staff_repo.claimed_with).to(equal((task.uuid, actor)))  # auto-claim implícito
    expect(human_repo.resolved_with).to(equal({"approved": True, "resolvedBy": actor}))
    expect(resolved.status).to(equal(HumanTaskStatus.RESOLVED))
    expect(handle.signals).to(
        equal([(TASK_RESOLVED_SIGNAL, [task.task_key, {"approved": True, "resolvedBy": actor}])])
    )


async def test_resolve_l1__out_of_scope_task_is_404():
    # El repo staff solo ve stage=review_l1 + INTERNAL_QUEUE: una L2 ⇒ None ⇒ 404.
    staff_repo = _FakeStaffTaskRepo(task=None)
    with pytest.raises(StaffTaskNotFoundError):
        await ResolveL1Task(
            task_id=uuid4(),
            staff_user=_staff(),
            resolution={"approved": True},
            staff_task_repository=staff_repo,
            human_task_repository=_FakeHumanTaskRepo(_task()),
            temporal_client=_FakeClient(_FakeHandle()),
        ).execute()


async def test_resolve_l1__claim_held_by_other_is_conflict():
    holder = f"staff:{uuid4()}"
    task = _task(claimed_by=holder)
    staff_repo = _FakeStaffTaskRepo(task, claim_result=None)

    try:
        await ResolveL1Task(
            task_id=task.uuid,
            staff_user=_staff(),
            resolution={"approved": True},
            staff_task_repository=staff_repo,
            human_task_repository=_FakeHumanTaskRepo(task),
            temporal_client=_FakeClient(_FakeHandle()),
        ).execute()
        raise AssertionError("expected StaffTaskClaimConflictError")
    except StaffTaskClaimConflictError as error:
        expect(error.context["holder"]).to(equal(holder))


async def test_resolve_l1__skips_claim_for_already_resolved_task():
    # Retry idempotente: la fila ya está resuelta — ResolveHumanTask re-señala.
    task = _task(status=HumanTaskStatus.RESOLVED, resolution={"approved": True})
    staff_repo = _FakeStaffTaskRepo(task, claim_result=None)
    handle = _FakeHandle()

    resolved = await ResolveL1Task(
        task_id=task.uuid,
        staff_user=_staff(),
        resolution={"approved": True},
        staff_task_repository=staff_repo,
        human_task_repository=_FakeHumanTaskRepo(task),
        temporal_client=_FakeClient(handle),
    ).execute()

    expect(staff_repo.claimed_with).to(be_none)  # no intenta claim
    expect(resolved.uuid).to(equal(task.uuid))
