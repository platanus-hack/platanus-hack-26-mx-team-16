"""E5 · §3.2: lock por caso — helper reutilizable ``ensure_case_not_locked``.

Lo consume el PATCH de campos del Inspection Bench (y cualquier mutación del
caso): APPROVAL abierta reclamada por OTRO ⇒ 423 ``case.locked`` con holder.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from expects import be_none, equal, expect

from src.common.domain.enums.human_tasks import HumanTaskKind, HumanTaskStatus
from src.workflows.application.human_tasks.case_lock import (
    CaseLockedError,
    ensure_case_not_locked,
    find_open_approval_task,
)
from src.workflows.domain.models.human_task import HumanTask

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_CASE = UUID("44444444-4444-4444-4444-444444444444")


def _task(kind: HumanTaskKind, claimed_by: str | None = None) -> HumanTask:
    return HumanTask(
        uuid=uuid4(),
        tenant_id=_TENANT,
        task_key=f"run-1:{uuid4().hex[:6]}",
        kind=kind,
        status=HumanTaskStatus.PENDING,
        case_id=_CASE,
        claimed_by=claimed_by,
    )


class _FakeRepo:
    def __init__(self, tasks):
        self._tasks = tasks

    async def list_open_by_case(self, case_id, tenant_id):
        return self._tasks


async def test_lock__approval_claimed_by_other_raises_423_with_holder():
    repo = _FakeRepo([_task(HumanTaskKind.APPROVAL, claimed_by="user:other")])

    with pytest.raises(CaseLockedError) as exc_info:
        await ensure_case_not_locked(repo, _CASE, _TENANT, "user:me")

    expect(exc_info.value.status_code).to(equal(423))
    expect(exc_info.value.code).to(equal("case.locked"))
    expect(exc_info.value.context["holder"]).to(equal("user:other"))


async def test_lock__holder_passes_and_gets_the_approval_back():
    approval = _task(HumanTaskKind.APPROVAL, claimed_by="user:me")
    repo = _FakeRepo([approval])

    result = await ensure_case_not_locked(repo, _CASE, _TENANT, "user:me")

    expect(result.uuid).to(equal(approval.uuid))


async def test_lock__unclaimed_approval_does_not_lock():
    approval = _task(HumanTaskKind.APPROVAL)
    repo = _FakeRepo([approval])

    result = await ensure_case_not_locked(repo, _CASE, _TENANT, "user:me")

    expect(result.uuid).to(equal(approval.uuid))


async def test_lock__clarifications_never_lock_the_case():
    repo = _FakeRepo([_task(HumanTaskKind.CLARIFICATION, claimed_by="user:other")])

    result = await ensure_case_not_locked(repo, _CASE, _TENANT, "user:me")

    expect(result).to(be_none)


async def test_find_open_approval__returns_oldest_approval_only():
    clarification = _task(HumanTaskKind.CLARIFICATION)
    first_approval = _task(HumanTaskKind.APPROVAL)
    second_approval = _task(HumanTaskKind.APPROVAL)
    repo = _FakeRepo([clarification, first_approval, second_approval])

    result = await find_open_approval_task(repo, _CASE, _TENANT)

    expect(result.uuid).to(equal(first_approval.uuid))
