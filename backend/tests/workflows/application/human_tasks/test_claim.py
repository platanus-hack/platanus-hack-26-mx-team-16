"""E5 · §3.2: claim/release tenant con UPDATE condicional (lock pesimista)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from expects import be_none, equal, expect

from src.common.domain.enums.human_tasks import HumanTaskKind, HumanTaskStatus
from src.workflows.application.human_tasks.claim import (
    ClaimHumanTask,
    HumanTaskNotClaimableError,
    HumanTaskNotFoundError,
)
from src.workflows.application.human_tasks.resolve import HumanTaskClaimConflictError
from src.workflows.domain.models.human_task import HumanTask

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_ACTOR = "user:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_OTHER = "user:bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def _task(
    status: HumanTaskStatus = HumanTaskStatus.PENDING, claimed_by: str | None = None
) -> HumanTask:
    return HumanTask(
        uuid=uuid4(),
        tenant_id=_TENANT,
        task_key="run-1:approval:review_l2",
        kind=HumanTaskKind.APPROVAL,
        status=status,
        stage="review_l2",
        claimed_by=claimed_by,
    )


class _FakeRepo:
    """Espejo del contrato del UPDATE condicional: ``claim``/``release``
    devuelven None cuando la condición no aplica (carrera perdida)."""

    def __init__(self, task: HumanTask | None):
        self._task = task
        self.released_with: tuple | None = None

    async def find_by_id(self, task_id, tenant_id):
        return self._task

    async def claim(self, task_id, tenant_id, actor):
        if (
            self._task is None
            or self._task.status != HumanTaskStatus.PENDING
            or (self._task.claimed_by and self._task.claimed_by != actor)
        ):
            return None
        self._task = self._task.model_copy(update={"claimed_by": actor})
        return self._task

    async def release(self, task_id, tenant_id, actor, force=False):
        self.released_with = (actor, force)
        if self._task is None or (not force and self._task.claimed_by != actor):
            return None
        self._task = self._task.model_copy(update={"claimed_by": None, "claimed_at": None})
        return self._task


async def test_claim__pending_unclaimed_sets_holder():
    repo = _FakeRepo(_task())

    claimed = await ClaimHumanTask(
        task_id=uuid4(), tenant_id=_TENANT, actor=_ACTOR, repository=repo
    ).execute()

    expect(claimed.claimed_by).to(equal(_ACTOR))


async def test_claim__is_idempotent_for_the_holder():
    repo = _FakeRepo(_task(claimed_by=_ACTOR))

    claimed = await ClaimHumanTask(
        task_id=uuid4(), tenant_id=_TENANT, actor=_ACTOR, repository=repo
    ).execute()

    expect(claimed.claimed_by).to(equal(_ACTOR))


async def test_claim__race_lost_raises_409_with_holder():
    # Carrera: el UPDATE condicional no tocó filas porque OTRO ya la reclamó.
    repo = _FakeRepo(_task(claimed_by=_OTHER))

    with pytest.raises(HumanTaskClaimConflictError) as exc_info:
        await ClaimHumanTask(
            task_id=uuid4(), tenant_id=_TENANT, actor=_ACTOR, repository=repo
        ).execute()

    expect(exc_info.value.status_code).to(equal(409))
    expect(exc_info.value.code).to(equal("human_task.already_claimed"))
    expect(exc_info.value.context["holder"]).to(equal(_OTHER))


async def test_claim__resolved_task_raises_not_claimable():
    repo = _FakeRepo(_task(status=HumanTaskStatus.RESOLVED))

    with pytest.raises(HumanTaskNotClaimableError) as exc_info:
        await ClaimHumanTask(
            task_id=uuid4(), tenant_id=_TENANT, actor=_ACTOR, repository=repo
        ).execute()

    expect(exc_info.value.code).to(equal("human_task.not_claimable"))


async def test_claim__missing_task_raises_404():
    with pytest.raises(HumanTaskNotFoundError):
        await ClaimHumanTask(
            task_id=uuid4(), tenant_id=_TENANT, actor=_ACTOR, repository=_FakeRepo(None)
        ).execute()


async def test_release__holder_clears_claim():
    repo = _FakeRepo(_task(claimed_by=_ACTOR))

    released = await ClaimHumanTask(
        task_id=uuid4(), tenant_id=_TENANT, actor=_ACTOR, repository=repo, release=True
    ).execute()

    expect(released.claimed_by).to(be_none)
    expect(repo.released_with).to(equal((_ACTOR, False)))


async def test_release__non_holder_raises_409_unless_forced():
    repo = _FakeRepo(_task(claimed_by=_OTHER))

    with pytest.raises(HumanTaskClaimConflictError):
        await ClaimHumanTask(
            task_id=uuid4(), tenant_id=_TENANT, actor=_ACTOR, repository=repo, release=True
        ).execute()

    forced = await ClaimHumanTask(
        task_id=uuid4(),
        tenant_id=_TENANT,
        actor=_ACTOR,
        repository=repo,
        release=True,
        force_release=True,  # tenant owner/admin
    ).execute()
    expect(forced.claimed_by).to(be_none)
