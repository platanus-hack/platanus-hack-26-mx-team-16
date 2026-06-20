"""Builders del módulo staff (E5 · W1 — solo cadena de datos, ADR 0001)."""

from datetime import datetime, timezone
from uuid import uuid4

from expects import be_false, be_none, be_true, equal, expect

from src.common.database.models.staff_access_event import StaffAccessEventORM
from src.common.database.models.staff_user import StaffUserORM
from src.staff.domain.models.staff_user import StaffRole, StaffUser, StaffUserStatus
from src.staff.infrastructure.builders.staff_access_event import build_staff_access_event
from src.staff.infrastructure.builders.staff_user import build_staff_user


def test_build_staff_user__maps_role_and_active_status():
    user_id = uuid4()
    orm = StaffUserORM(
        uuid=uuid4(),
        user_id=user_id,
        role="staff_analyst_l1",
        status="active",
    )

    staff = build_staff_user(orm)

    expect(staff.user_id).to(equal(user_id))
    expect(staff.role).to(equal(StaffRole.STAFF_ANALYST_L1))
    expect(staff.status).to(equal(StaffUserStatus.ACTIVE))
    expect(staff.is_active).to(be_true)
    expect(staff.revoked_at).to(be_none)


def test_build_staff_user__revoked_is_not_active():
    revoked_at = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)
    orm = StaffUserORM(
        uuid=uuid4(),
        user_id=uuid4(),
        role="staff_admin",
        status="revoked",
        revoked_at=revoked_at,
    )

    staff = build_staff_user(orm)

    expect(staff.role).to(equal(StaffRole.STAFF_ADMIN))
    expect(staff.status).to(equal(StaffUserStatus.REVOKED))
    expect(staff.is_active).to(be_false)
    expect(staff.revoked_at).to(equal(revoked_at))


def test_staff_user_persist_dict__serializes_enum_values():
    staff = StaffUser(
        uuid=uuid4(),
        user_id=uuid4(),
        role=StaffRole.STAFF_ANALYST_L1,
        status=StaffUserStatus.ACTIVE,
    )

    persist = staff.persist_dict

    expect(persist["role"]).to(equal("staff_analyst_l1"))
    expect(persist["status"]).to(equal("active"))
    expect(persist["user_id"]).to(equal(staff.user_id))
    expect(persist["revoked_at"]).to(be_none)


def test_build_staff_access_event__maps_metadata_column():
    staff_user_id = uuid4()
    tenant_id = uuid4()
    task_id = uuid4()
    metadata = {"route": "/staff/v1/tasks/{task_id}/claim", "method": "POST"}
    orm = StaffAccessEventORM(
        uuid=uuid4(),
        staff_user_id=staff_user_id,
        action="tasks.claim",
        tenant_id=tenant_id,
        task_id=task_id,
        request_id="req-123",
        ip="10.0.0.1",
        event_metadata=metadata,
    )

    event = build_staff_access_event(orm)

    expect(event.staff_user_id).to(equal(staff_user_id))
    expect(event.action).to(equal("tasks.claim"))
    expect(event.tenant_id).to(equal(tenant_id))
    expect(event.case_id).to(be_none)
    expect(event.task_id).to(equal(task_id))
    expect(event.request_id).to(equal("req-123"))
    expect(event.ip).to(equal("10.0.0.1"))
    expect(event.metadata).to(equal(metadata))


def test_build_staff_access_event__none_metadata_becomes_empty_dict():
    orm = StaffAccessEventORM(
        uuid=uuid4(),
        staff_user_id=uuid4(),
        action="audit.list",
    )

    event = build_staff_access_event(orm)

    expect(event.metadata).to(equal({}))


def test_staff_access_event_persist_dict__maps_metadata_to_orm_attribute():
    event_uuid = uuid4()
    staff_user_id = uuid4()
    orm = StaffAccessEventORM(
        uuid=event_uuid,
        staff_user_id=staff_user_id,
        action="cases.read",
        event_metadata={"case": "x"},
    )

    event = build_staff_access_event(orm)
    persist = event.persist_dict

    expect(persist["staff_user_id"]).to(equal(staff_user_id))
    expect(persist["action"]).to(equal("cases.read"))
    expect(persist["event_metadata"]).to(equal({"case": "x"}))
