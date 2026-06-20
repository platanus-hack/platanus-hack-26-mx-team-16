"""E5 · W4: StaffAccessEventRepository — append-only + filtros del audit."""

from uuid import uuid4

import pytest
from expects import equal, expect, have_len

from src.staff.domain.models.staff_access_event import StaffAccessEvent
from src.staff.infrastructure.repositories.sql_staff_access_event import (
    SQLStaffAccessEventRepository,
)


@pytest.fixture
def events_repo(async_session):
    return SQLStaffAccessEventRepository(session=async_session)


def _event(staff_user_id, action="tasks.list", tenant_id=None, **overrides) -> StaffAccessEvent:
    defaults = dict(
        uuid=uuid4(),
        staff_user_id=staff_user_id,
        action=action,
        tenant_id=tenant_id,
        request_id=f"req-{uuid4().hex[:8]}",
        ip="10.0.0.1",
        metadata={"path": "/staff/v1/tasks"},
    )
    defaults.update(overrides)
    return StaffAccessEvent(**defaults)


async def test_append_and_list__roundtrip(events_repo, staff_user_orm):
    created = await events_repo.append(_event(staff_user_orm.uuid, action="cases.view"))

    listed = await events_repo.list(staff_user_id=staff_user_orm.uuid, action="cases.view")

    expect(listed).to(have_len(1))
    expect(listed[0].uuid).to(equal(created.uuid))
    expect(listed[0].action).to(equal("cases.view"))
    expect(listed[0].metadata).to(equal({"path": "/staff/v1/tasks"}))


async def test_list__filters_by_tenant_and_action(events_repo, staff_user_orm, tenant_orm):
    await events_repo.append(_event(staff_user_orm.uuid, action="tasks.list"))
    await events_repo.append(
        _event(staff_user_orm.uuid, action="tasks.claim", tenant_id=tenant_orm.uuid)
    )

    by_tenant = await events_repo.list(tenant_id=tenant_orm.uuid)
    expect(by_tenant).to(have_len(1))
    expect(by_tenant[0].action).to(equal("tasks.claim"))

    by_action = await events_repo.list(staff_user_id=staff_user_orm.uuid, action="tasks.list")
    expect(by_action).to(have_len(1))
    expect(by_action[0].tenant_id).to(equal(None))
