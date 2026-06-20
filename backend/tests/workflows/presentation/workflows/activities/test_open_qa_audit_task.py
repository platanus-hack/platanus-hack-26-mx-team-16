"""E6 §3: integration test de la activity ``open_qa_audit_task``.

Mismo patrón que ``test_case_phase_activities``: se committea el seed vía la
sesión del test y la activity abre SU propia sesión vía ``session_maker``; un
``finally`` limpia las filas committeadas.

Cubre el universo "auto-aprobado": la QA task se abre SOLO si existe un
``review.skipped`` y NO un ``review.approved`` humano. La task es fire-and-forget
(``pipeline_run_id`` None) y deja un ``qa.sampled`` en el timeline.
"""

from uuid import uuid4

import pytest
from expects import be_none, equal, expect
from sqlalchemy import delete

from src.common.database.config import get_database_config
from src.common.database.models.case_event import CaseEventORM
from src.common.database.models.human_task import HumanTaskORM
from src.common.domain.entities.workflows.case_runtime import OpenQaAuditTaskInput
from src.common.domain.enums.human_tasks import HumanTaskKind
from src.workflows.domain.models.case_event import CaseEvent
from src.workflows.infrastructure.repositories.sql_case_event import SQLCaseEventRepository
from src.workflows.infrastructure.repositories.sql_human_task import SQLHumanTaskRepository
from src.workflows.presentation.workflows.activities.case_runtime_activities import (
    CaseRuntimeActivities,
)


@pytest.fixture
def session_maker():
    return get_database_config().session_maker


@pytest.fixture
def qa_activities(session_maker):
    return CaseRuntimeActivities(session_maker=session_maker)


async def _seed_event(session_maker, tenant_id, case_id, type_):
    async with session_maker() as session:
        await SQLCaseEventRepository(session).create(
            CaseEvent(uuid=uuid4(), tenant_id=tenant_id, case_id=case_id, type=type_, actor="system")
        )
        await session.commit()


async def _cleanup(session_maker, tenant_id) -> None:
    async with session_maker() as cleanup:
        await cleanup.execute(delete(HumanTaskORM).where(HumanTaskORM.tenant_id == tenant_id))
        await cleanup.execute(delete(CaseEventORM).where(CaseEventORM.tenant_id == tenant_id))
        await cleanup.commit()


def _input(tenant_id, workflow_id, case_id) -> OpenQaAuditTaskInput:
    return OpenQaAuditTaskInput(
        task_key=f"run-{uuid4().hex[:8]}:qa",
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        case_id=case_id,
        run_id="run-x",
    )


async def test_open_qa_audit_task__auto_approved_opens_qa_task_and_emits_event(
    qa_activities, session_maker, async_session, tenant_orm, workflow_orm, case_orm
):
    await async_session.commit()
    try:
        # Caso auto-aprobado: review.skipped presente, sin review.approved.
        await _seed_event(session_maker, tenant_orm.uuid, case_orm.uuid, "review.skipped")

        result = await qa_activities.open_qa_audit_task(
            _input(tenant_orm.uuid, workflow_orm.uuid, case_orm.uuid)
        )

        expect(result.created).to(equal(True))
        expect(result.task_id is not None).to(equal(True))

        async with session_maker() as session:
            task = await SQLHumanTaskRepository(session).find_by_id(result.task_id, tenant_orm.uuid)
            # kind=QA, stage L1 (cola staff), sin run pausado.
            expect(task.kind).to(equal(HumanTaskKind.QA))
            expect(task.stage).to(equal("review_l1"))
            expect(task.pipeline_run_id).to(be_none)

            events = await SQLCaseEventRepository(session).list_by_case(case_orm.uuid, tenant_orm.uuid)
            expect("qa.sampled" in {e.type for e in events}).to(equal(True))
    finally:
        await _cleanup(session_maker, tenant_orm.uuid)


async def test_open_qa_audit_task__human_approved_is_noop(
    qa_activities, session_maker, async_session, tenant_orm, workflow_orm, case_orm
):
    await async_session.commit()
    try:
        # Un humano aprobó ⇒ NO es auto-aprobado ⇒ no se audita.
        await _seed_event(session_maker, tenant_orm.uuid, case_orm.uuid, "review.skipped")
        await _seed_event(session_maker, tenant_orm.uuid, case_orm.uuid, "review.approved")

        result = await qa_activities.open_qa_audit_task(
            _input(tenant_orm.uuid, workflow_orm.uuid, case_orm.uuid)
        )

        expect(result.created).to(equal(False))
        expect(result.task_id).to(be_none)
        async with session_maker() as session:
            events = await SQLCaseEventRepository(session).list_by_case(case_orm.uuid, tenant_orm.uuid)
            expect("qa.sampled" in {e.type for e in events}).to(equal(False))
    finally:
        await _cleanup(session_maker, tenant_orm.uuid)


async def test_open_qa_audit_task__no_review_skipped_is_noop(
    qa_activities, session_maker, async_session, tenant_orm, workflow_orm, case_orm
):
    await async_session.commit()
    try:
        # Sin review.skipped no hay universo QA ⇒ no-op.
        result = await qa_activities.open_qa_audit_task(
            _input(tenant_orm.uuid, workflow_orm.uuid, case_orm.uuid)
        )

        expect(result.created).to(equal(False))
        expect(result.task_id).to(be_none)
    finally:
        await _cleanup(session_maker, tenant_orm.uuid)


async def test_open_qa_audit_task__is_idempotent_on_task_key(
    qa_activities, session_maker, async_session, tenant_orm, workflow_orm, case_orm
):
    await async_session.commit()
    try:
        # Replay/retry: el mismo task_key no crea dos tasks ni dos qa.sampled.
        await _seed_event(session_maker, tenant_orm.uuid, case_orm.uuid, "review.skipped")
        payload = _input(tenant_orm.uuid, workflow_orm.uuid, case_orm.uuid)

        first = await qa_activities.open_qa_audit_task(payload)
        second = await qa_activities.open_qa_audit_task(payload)

        expect(second.task_id).to(equal(first.task_id))
        async with session_maker() as session:
            events = await SQLCaseEventRepository(session).list_by_case(case_orm.uuid, tenant_orm.uuid)
            sampled = [e for e in events if e.type == "qa.sampled"]
            expect(len(sampled)).to(equal(1))
    finally:
        await _cleanup(session_maker, tenant_orm.uuid)
