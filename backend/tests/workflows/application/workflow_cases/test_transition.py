"""E4 · diseño §1: TransitionCaseStatus — choke point de la máquina de estados.

Valida legalidad, persiste el status y appendea ``case_events``
(``status.changed``). Mismo estado ⇒ no-op (sin update, sin evento).
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from expects import be_empty, be_false, be_none, be_true, equal, expect

from src.common.domain.enums.workflow_cases import WorkflowCaseStatus
from src.common.domain.exceptions.processing import CaseNotFoundError
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.workflows.application.workflow_cases.transition import (
    STATUS_CHANGED_EVENT,
    TransitionCaseStatus,
)
from src.workflows.domain.services.case_state_machine import IllegalCaseTransitionError

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")


def _case(status: WorkflowCaseStatus) -> WorkflowCase:
    return WorkflowCase(
        uuid=uuid4(),
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        name="Case",
        status=status,
    )


class _FakeCaseRepo:
    def __init__(self, case: WorkflowCase | None):
        self._case = case
        self.updated_with: WorkflowCase | None = None

    async def find_by_id(self, case_id, tenant_id):
        return self._case

    async def update(self, case):
        self.updated_with = case
        return case


class _FakeEventRepo:
    def __init__(self):
        self.created = []

    async def create(self, event):
        self.created.append(event)
        return event


def _use_case(case_repo, event_repo, case_id, to_status, **kwargs) -> TransitionCaseStatus:
    return TransitionCaseStatus(
        tenant_id=_TENANT,
        case_id=case_id,
        to_status=to_status,
        case_repository=case_repo,
        case_event_repository=event_repo,
        **kwargs,
    )


async def test_transition__legal_persists_and_appends_event():
    case = _case(WorkflowCaseStatus.RECEIVING)
    case_repo, event_repo = _FakeCaseRepo(case), _FakeEventRepo()

    result = await _use_case(
        case_repo, event_repo, case.uuid, WorkflowCaseStatus.PROCESSING, reason="ready", actor="system"
    ).execute()

    expect(result.changed).to(be_true)
    expect(result.case.status).to(equal(WorkflowCaseStatus.PROCESSING))
    expect(case_repo.updated_with.status).to(equal(WorkflowCaseStatus.PROCESSING))
    expect(len(event_repo.created)).to(equal(1))
    event = event_repo.created[0]
    expect(event.type).to(equal(STATUS_CHANGED_EVENT))
    expect(event.case_id).to(equal(case.uuid))
    expect(event.payload).to(equal({"from": "RECEIVING", "to": "PROCESSING", "reason": "ready"}))
    expect(event.actor).to(equal("system"))


async def test_transition__same_status_is_noop():
    case = _case(WorkflowCaseStatus.PROCESSING)
    case_repo, event_repo = _FakeCaseRepo(case), _FakeEventRepo()

    result = await _use_case(case_repo, event_repo, case.uuid, WorkflowCaseStatus.PROCESSING).execute()

    expect(result.changed).to(be_false)
    expect(case_repo.updated_with).to(be_none)
    expect(event_repo.created).to(be_empty)


async def test_transition__illegal_raises_409_and_persists_nothing():
    case = _case(WorkflowCaseStatus.COMPLETED)
    case_repo, event_repo = _FakeCaseRepo(case), _FakeEventRepo()

    with pytest.raises(IllegalCaseTransitionError) as exc_info:
        await _use_case(case_repo, event_repo, case.uuid, WorkflowCaseStatus.PROCESSING).execute()

    expect(exc_info.value.status_code).to(equal(409))
    expect(case_repo.updated_with).to(be_none)
    expect(event_repo.created).to(be_empty)


async def test_transition__without_reason_omits_key():
    case = _case(WorkflowCaseStatus.PROCESSING)
    case_repo, event_repo = _FakeCaseRepo(case), _FakeEventRepo()

    await _use_case(case_repo, event_repo, case.uuid, WorkflowCaseStatus.ANALYZING).execute()

    expect(event_repo.created[0].payload).to(equal({"from": "PROCESSING", "to": "ANALYZING"}))


async def test_transition__case_not_found():
    case_repo, event_repo = _FakeCaseRepo(None), _FakeEventRepo()

    with pytest.raises(CaseNotFoundError):
        await _use_case(case_repo, event_repo, uuid4(), WorkflowCaseStatus.PROCESSING).execute()
