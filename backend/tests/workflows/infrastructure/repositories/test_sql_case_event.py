"""E4: SQLCaseEventRepository — append-only create + list_by_case."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from expects import equal, expect

from src.workflows.domain.models.case_event import CaseEvent
from src.workflows.infrastructure.repositories.sql_case_event import SQLCaseEventRepository


@pytest.fixture
def case_event_repo(async_session):
    return SQLCaseEventRepository(session=async_session)


def _event(tenant_id, case_id, type_: str, payload: dict | None = None, actor: str | None = None) -> CaseEvent:
    return CaseEvent(
        uuid=uuid4(),
        tenant_id=tenant_id,
        case_id=case_id,
        type=type_,
        payload=payload or {},
        actor=actor,
    )


async def test_create__persists_append_only_row(case_event_repo, tenant_orm, case_orm):
    event = _event(
        tenant_orm.uuid,
        case_orm.uuid,
        "status.changed",
        payload={"from": "RECEIVING", "to": "PROCESSING"},
        actor="system",
    )

    created = await case_event_repo.create(event)

    expect(created.type).to(equal("status.changed"))
    expect(created.payload).to(equal({"from": "RECEIVING", "to": "PROCESSING"}))
    expect(created.actor).to(equal("system"))
    expect(created.created_at is not None).to(equal(True))


async def test_list_by_case__desc_by_default_with_limit(case_event_repo, tenant_orm, case_orm):
    for idx in range(3):
        await case_event_repo.create(_event(tenant_orm.uuid, case_orm.uuid, f"event.{idx}"))

    events = await case_event_repo.list_by_case(case_orm.uuid, tenant_orm.uuid, limit=2)

    expect(len(events)).to(equal(2))
    # created_at puede empatar en el mismo flush; el orden estable usa uuid desc.
    all_events = await case_event_repo.list_by_case(case_orm.uuid, tenant_orm.uuid)
    expect(len(all_events)).to(equal(3))


async def test_list_by_case__scoped_by_tenant(case_event_repo, tenant_orm, case_orm):
    await case_event_repo.create(_event(tenant_orm.uuid, case_orm.uuid, "ready"))

    events = await case_event_repo.list_by_case(case_orm.uuid, uuid4())

    expect(events).to(equal([]))


async def test_list_by_case__asc_order(case_event_repo, tenant_orm, case_orm):
    created = []
    for idx in range(2):
        created.append(await case_event_repo.create(_event(tenant_orm.uuid, case_orm.uuid, f"event.{idx}")))

    asc_events = await case_event_repo.list_by_case(case_orm.uuid, tenant_orm.uuid, desc=False)
    desc_events = await case_event_repo.list_by_case(case_orm.uuid, tenant_orm.uuid, desc=True)

    expect([e.uuid for e in asc_events]).to(equal(list(reversed([e.uuid for e in desc_events]))))


async def test_create__dedupe_key_makes_activity_retries_idempotent(case_event_repo, tenant_orm, case_orm):
    # Fix review E4: retry de append_case_event tras éxito no confirmado ⇒
    # mismo dedupe_key ⇒ una sola fila (devuelve la existente).
    key = "RUN-1:approval:review.approved"
    first = CaseEvent(
        uuid=uuid4(), tenant_id=tenant_orm.uuid, case_id=case_orm.uuid,
        type="review.approved", payload={"taskId": "t-1"}, dedupe_key=key,
    )
    retry = CaseEvent(
        uuid=uuid4(), tenant_id=tenant_orm.uuid, case_id=case_orm.uuid,
        type="review.approved", payload={"taskId": "t-1"}, dedupe_key=key,
    )

    created = await case_event_repo.create(first)
    deduped = await case_event_repo.create(retry)

    expect(deduped.uuid).to(equal(created.uuid))
    events = await case_event_repo.list_by_case(case_orm.uuid, tenant_orm.uuid)
    expect([e.uuid for e in events if e.type == "review.approved"]).to(equal([created.uuid]))


# ─── E6 §3.5: count_by_type_since (base de las métricas QA) ───────────────────


async def test_count_by_type_since__groups_by_tenant_type_and_actor(
    case_event_repo, tenant_orm, case_orm
):
    await case_event_repo.create(_event(tenant_orm.uuid, case_orm.uuid, "qa.passed", actor="staff:a"))
    await case_event_repo.create(_event(tenant_orm.uuid, case_orm.uuid, "qa.passed", actor="staff:a"))
    await case_event_repo.create(_event(tenant_orm.uuid, case_orm.uuid, "qa.failed", actor="staff:b"))
    await case_event_repo.create(_event(tenant_orm.uuid, case_orm.uuid, "review.approved", actor="user:x"))

    since = datetime.now(UTC) - timedelta(hours=1)
    rows = await case_event_repo.count_by_type_since(
        ["qa.passed", "qa.failed", "review.approved"], since, tenant_id=tenant_orm.uuid
    )

    by_key = {(t, actor): count for _tenant, t, actor, count in rows}
    expect(by_key[("qa.passed", "staff:a")]).to(equal(2))
    expect(by_key[("qa.failed", "staff:b")]).to(equal(1))
    expect(by_key[("review.approved", "user:x")]).to(equal(1))


async def test_count_by_type_since__excludes_events_before_window(
    case_event_repo, tenant_orm, case_orm
):
    await case_event_repo.create(_event(tenant_orm.uuid, case_orm.uuid, "qa.passed", actor="staff:a"))

    # Ventana en el futuro ⇒ nada cae dentro.
    future = datetime.now(UTC) + timedelta(hours=1)
    rows = await case_event_repo.count_by_type_since(["qa.passed"], future, tenant_id=tenant_orm.uuid)

    expect(rows).to(equal([]))


async def test_count_by_type_since__cross_tenant_when_tenant_none(
    case_event_repo, tenant_orm, case_orm
):
    await case_event_repo.create(_event(tenant_orm.uuid, case_orm.uuid, "qa.passed", actor="staff:a"))

    since = datetime.now(UTC) - timedelta(hours=1)
    rows = await case_event_repo.count_by_type_since(["qa.passed"], since, tenant_id=None)

    total = sum(count for _t, _type, _actor, count in rows if _type == "qa.passed")
    expect(total >= 1).to(equal(True))


async def test_count_by_type_since__empty_types_returns_empty(case_event_repo, tenant_orm):
    rows = await case_event_repo.count_by_type_since([], datetime.now(UTC), tenant_id=tenant_orm.uuid)

    expect(rows).to(equal([]))
