"""E5 · AddCaseComment: case_event ``comment.added`` con actor y SIN dedupe."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from expects import be_none, equal, expect, have_length

from src.common.domain.exceptions.processing import CaseNotFoundError
from src.workflows.application.workflow_cases.commenter import AddCaseComment

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")
_CASE = UUID("44444444-4444-4444-4444-444444444444")


class _FakeCaseRepo:
    def __init__(self, case):
        self._case = case

    async def find_by_id(self, case_id, tenant_id):
        return self._case


class _FakeEventRepo:
    def __init__(self):
        self.created: list = []

    async def create(self, event):
        self.created.append(event)
        return event


def _use_case(events, *, case=..., workflow_id=None, actor="user:abc"):
    resolved_case = SimpleNamespace(uuid=_CASE, workflow_id=_WORKFLOW) if case is ... else case
    return AddCaseComment(
        tenant_id=_TENANT,
        case_id=_CASE,
        body="ojo con la CI de la persona 2",
        case_repository=_FakeCaseRepo(resolved_case),
        case_event_repository=events,
        actor=actor,
        workflow_id=workflow_id,
    )


async def test_comment__creates_event_with_actor_and_no_dedupe():
    events = _FakeEventRepo()
    event = await _use_case(events).execute()

    expect(events.created).to(have_length(1))
    expect(event.type).to(equal("comment.added"))
    expect(event.payload).to(equal({"body": "ojo con la CI de la persona 2"}))
    expect(event.actor).to(equal("user:abc"))
    expect(event.dedupe_key).to(be_none)  # cada comentario es único


async def test_comment__repeated_body_creates_distinct_events():
    events = _FakeEventRepo()
    first = await _use_case(events).execute()
    second = await _use_case(events).execute()

    expect(events.created).to(have_length(2))
    expect(str(first.uuid) == str(second.uuid)).to(equal(False))


async def test_comment__case_of_another_workflow_is_404():
    events = _FakeEventRepo()
    with pytest.raises(CaseNotFoundError):
        await _use_case(events, workflow_id=uuid4()).execute()


async def test_comment__missing_case_is_404():
    events = _FakeEventRepo()
    with pytest.raises(CaseNotFoundError):
        await _use_case(events, case=None).execute()
