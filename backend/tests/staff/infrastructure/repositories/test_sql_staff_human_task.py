"""E5 · W4: StaffHumanTaskRepository — cola L1 cross-tenant acotada + claim."""

from uuid import uuid4

import pytest
from expects import be_none, equal, expect, have_len

from src.staff.infrastructure.repositories.sql_staff_human_task import (
    SQLStaffHumanTaskRepository,
)
from tests.staff.conftest import make_l1_task_orm


@pytest.fixture
def staff_tasks_repo(async_session):
    return SQLStaffHumanTaskRepository(session=async_session)


async def test_list_open_l1__is_cross_tenant_with_tenant_context(
    staff_tasks_repo, async_session, tenant_orm, other_tenant_orm
):
    task_a = make_l1_task_orm(tenant_orm.uuid)
    task_b = make_l1_task_orm(other_tenant_orm.uuid)
    async_session.add_all([task_a, task_b])
    await async_session.flush()

    items = await staff_tasks_repo.list_open_l1()

    uuids = {item.task.uuid for item in items}
    expect(uuids.issuperset({task_a.uuid, task_b.uuid})).to(equal(True))
    by_uuid = {item.task.uuid: item for item in items}
    expect(by_uuid[task_a.uuid].tenant_name).to(equal(tenant_orm.name))
    expect(by_uuid[task_b.uuid].tenant_slug).to(equal(other_tenant_orm.slug))


async def test_list_open_l1__excludes_out_of_scope_tasks(
    staff_tasks_repo, async_session, tenant_orm
):
    in_scope = make_l1_task_orm(tenant_orm.uuid)
    l2_task = make_l1_task_orm(tenant_orm.uuid, stage="review_l2")
    external = make_l1_task_orm(tenant_orm.uuid, assignee_mode="external_callback")
    legacy_no_stage = make_l1_task_orm(tenant_orm.uuid, stage=None)
    async_session.add_all([in_scope, l2_task, external, legacy_no_stage])
    await async_session.flush()

    items = await staff_tasks_repo.list_open_l1(tenant_id=tenant_orm.uuid)

    expect(items).to(have_len(1))
    expect(items[0].task.uuid).to(equal(in_scope.uuid))

    # find_by_id respeta el MISMO alcance: L2/external/legacy son invisibles.
    expect(await staff_tasks_repo.find_by_id(l2_task.uuid)).to(be_none)
    expect(await staff_tasks_repo.find_by_id(external.uuid)).to(be_none)
    expect(await staff_tasks_repo.find_by_id(legacy_no_stage.uuid)).to(be_none)
    found = await staff_tasks_repo.find_by_id(in_scope.uuid)
    expect(found.uuid).to(equal(in_scope.uuid))


async def test_list_open_l1__filters_by_status(staff_tasks_repo, async_session, tenant_orm):
    pending = make_l1_task_orm(tenant_orm.uuid)
    resolved = make_l1_task_orm(tenant_orm.uuid, status="resolved")
    async_session.add_all([pending, resolved])
    await async_session.flush()

    default_list = await staff_tasks_repo.list_open_l1(tenant_id=tenant_orm.uuid)
    expect({i.task.uuid for i in default_list}).to(equal({pending.uuid}))

    resolved_list = await staff_tasks_repo.list_open_l1(
        tenant_id=tenant_orm.uuid, status="resolved"
    )
    expect({i.task.uuid for i in resolved_list}).to(equal({resolved.uuid}))


async def test_list_open_l1__segments_by_kind(staff_tasks_repo, async_session, tenant_orm):
    # E6 §3: la cola staff puede aislar QA de las aprobaciones (ambos en L1).
    approval = make_l1_task_orm(tenant_orm.uuid, kind="approval")
    qa = make_l1_task_orm(tenant_orm.uuid, kind="qa")
    async_session.add_all([approval, qa])
    await async_session.flush()

    both = await staff_tasks_repo.list_open_l1(tenant_id=tenant_orm.uuid)
    expect({i.task.uuid for i in both}).to(equal({approval.uuid, qa.uuid}))

    only_qa = await staff_tasks_repo.list_open_l1(tenant_id=tenant_orm.uuid, kind="qa")
    expect({i.task.uuid for i in only_qa}).to(equal({qa.uuid}))

    only_approval = await staff_tasks_repo.list_open_l1(tenant_id=tenant_orm.uuid, kind="approval")
    expect({i.task.uuid for i in only_approval}).to(equal({approval.uuid}))


async def test_find_l1_task_by_case__gates_cross_tenant_pii(
    staff_tasks_repo, async_session, tenant_orm
):
    # C6: el gate de PII cross-tenant. Solo hay match si existe una tarea
    # L1 servible (review_l1 + INTERNAL_QUEUE) ligada al case_id.
    served_case = uuid4()
    l2_case = uuid4()
    no_task_case = uuid4()

    l1 = make_l1_task_orm(tenant_orm.uuid, case_id=served_case)
    l2 = make_l1_task_orm(tenant_orm.uuid, case_id=l2_case, stage="review_l2")
    external = make_l1_task_orm(
        tenant_orm.uuid, case_id=l2_case, assignee_mode="external_callback"
    )
    async_session.add_all([l1, l2, external])
    await async_session.flush()

    found = await staff_tasks_repo.find_l1_task_by_case(served_case)
    expect(found.uuid).to(equal(l1.uuid))

    # Caso con solo L2/external ⇒ fuera de alcance ⇒ None (404 aguas arriba).
    expect(await staff_tasks_repo.find_l1_task_by_case(l2_case)).to(be_none)
    # Caso sin ninguna tarea ⇒ None (la fuga cross-tenant que C6 cierra).
    expect(await staff_tasks_repo.find_l1_task_by_case(no_task_case)).to(be_none)


async def test_find_l1_task_by_case__prefers_pending_over_resolved(
    staff_tasks_repo, async_session, tenant_orm
):
    case_id = uuid4()
    resolved = make_l1_task_orm(tenant_orm.uuid, case_id=case_id, status="resolved")
    pending = make_l1_task_orm(tenant_orm.uuid, case_id=case_id)
    async_session.add_all([resolved, pending])
    await async_session.flush()

    found = await staff_tasks_repo.find_l1_task_by_case(case_id)
    expect(found.uuid).to(equal(pending.uuid))


async def test_claim__is_conditional_and_idempotent_per_actor(
    staff_tasks_repo, async_session, tenant_orm
):
    task = make_l1_task_orm(tenant_orm.uuid)
    async_session.add(task)
    await async_session.flush()
    actor = f"staff:{uuid4()}"
    rival = f"staff:{uuid4()}"

    claimed = await staff_tasks_repo.claim(task.uuid, actor)
    expect(claimed.claimed_by).to(equal(actor))
    expect(claimed.claimed_at).not_to(be_none)

    # Mismo actor: re-claim legal (idempotente).
    again = await staff_tasks_repo.claim(task.uuid, actor)
    expect(again.claimed_by).to(equal(actor))

    # Otro actor: 0 filas — el use case lo traduce a 409 con holder.
    expect(await staff_tasks_repo.claim(task.uuid, rival)).to(be_none)


async def test_claim__rejects_non_pending_tasks(staff_tasks_repo, async_session, tenant_orm):
    task = make_l1_task_orm(tenant_orm.uuid, status="resolved")
    async_session.add(task)
    await async_session.flush()

    expect(await staff_tasks_repo.claim(task.uuid, f"staff:{uuid4()}")).to(be_none)


async def test_release__only_holder_unless_forced(staff_tasks_repo, async_session, tenant_orm):
    task = make_l1_task_orm(tenant_orm.uuid)
    async_session.add(task)
    await async_session.flush()
    holder = f"staff:{uuid4()}"
    rival = f"staff:{uuid4()}"
    await staff_tasks_repo.claim(task.uuid, holder)

    expect(await staff_tasks_repo.release(task.uuid, rival)).to(be_none)

    released = await staff_tasks_repo.release(task.uuid, holder)
    expect(released.claimed_by).to(be_none)
    expect(released.claimed_at).to(be_none)

    # force=True (staff_admin) libera el claim de cualquiera.
    await staff_tasks_repo.claim(task.uuid, holder)
    forced = await staff_tasks_repo.release(task.uuid, rival, force=True)
    expect(forced.claimed_by).to(be_none)
