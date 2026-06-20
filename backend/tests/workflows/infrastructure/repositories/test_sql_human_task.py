"""E5 · W1: roundtrip de `stage`/`claimed_by`/`claimed_at` en SQLHumanTaskRepository."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from expects import be_none, equal, expect

from src.common.domain.enums.human_tasks import HumanTaskKind, HumanTaskStatus
from src.workflows.domain.models.human_task import HumanTask
from src.workflows.infrastructure.repositories.sql_human_task import SQLHumanTaskRepository


@pytest.fixture
def human_task_repo(async_session):
    return SQLHumanTaskRepository(session=async_session)


async def test_upsert__persists_stage_and_claim(human_task_repo, tenant_orm):
    claimed_at = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)
    claimed_by = f"staff:{uuid4()}"
    task = HumanTask(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        task_key=f"CASE#{uuid4().hex}:approval:review_l1",
        kind=HumanTaskKind.APPROVAL,
        stage="review_l1",
        claimed_by=claimed_by,
        claimed_at=claimed_at,
    )

    created = await human_task_repo.upsert(task)

    expect(created.stage).to(equal("review_l1"))
    expect(created.claimed_by).to(equal(claimed_by))
    expect(created.claimed_at).to(equal(claimed_at))

    found = await human_task_repo.find_by_id(task.uuid, tenant_orm.uuid)
    expect(found.stage).to(equal("review_l1"))
    expect(found.claimed_by).to(equal(claimed_by))
    expect(found.claimed_at).to(equal(claimed_at))


async def test_upsert__without_stage_keeps_e4_compat(human_task_repo, tenant_orm):
    task = HumanTask(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        task_key=f"CASE#{uuid4().hex}:approval",
        kind=HumanTaskKind.APPROVAL,
    )

    created = await human_task_repo.upsert(task)

    expect(created.stage).to(be_none)
    expect(created.claimed_by).to(be_none)
    expect(created.claimed_at).to(be_none)


async def test_upsert__is_idempotent_by_task_key(human_task_repo, tenant_orm):
    task_key = f"CASE#{uuid4().hex}:approval:review_l2"
    first = HumanTask(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        task_key=task_key,
        kind=HumanTaskKind.APPROVAL,
        stage="review_l2",
    )
    await human_task_repo.upsert(first)

    replay = HumanTask(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        task_key=task_key,
        kind=HumanTaskKind.APPROVAL,
        stage="review_l2",
    )
    second = await human_task_repo.upsert(replay)

    expect(second.uuid).to(equal(first.uuid))
    expect(second.stage).to(equal("review_l2"))


# ─── E5 §C5: resolve() es UPDATE condicional (carrera / doble-submit) ─────────


async def test_resolve__conditional_update_first_writer_wins(human_task_repo, tenant_orm):
    """Dos resolves sobre la MISMA fila pending: el primero escribe su
    resolución y la marca RESOLVED; el segundo encuentra 0 filas en el UPDATE
    condicional y devuelve la resolución ALMACENADA sin sobrescribirla."""
    task = HumanTask(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        task_key=f"CASE#{uuid4().hex}:approval:review_l2",
        kind=HumanTaskKind.APPROVAL,
    )
    await human_task_repo.upsert(task)

    winner = await human_task_repo.resolve(task.uuid, tenant_orm.uuid, {"approved": True})
    expect(winner.status).to(equal(HumanTaskStatus.RESOLVED))
    expect(winner.resolution).to(equal({"approved": True}))

    # Segundo resolve (carrera perdida / doble-submit): 0 filas en el UPDATE
    # condicional ⇒ re-lee y devuelve la resolución del ganador, NO la nueva.
    loser = await human_task_repo.resolve(task.uuid, tenant_orm.uuid, {"approved": False})
    expect(loser.status).to(equal(HumanTaskStatus.RESOLVED))
    expect(loser.resolution).to(equal({"approved": True}))


async def test_resolve__unknown_task_returns_none(human_task_repo, tenant_orm):
    """0 filas por inexistencia (no por carrera) ⇒ None, para que el use case
    distinga 404 de 'ya resuelta'."""
    result = await human_task_repo.resolve(uuid4(), tenant_orm.uuid, {"approved": True})
    expect(result).to(be_none)
