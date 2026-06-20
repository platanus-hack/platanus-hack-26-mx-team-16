"""Integration tests de las activities case-scope del intérprete (E2).

Mismo patrón que ``test_update_processing_job_status``: se siembra vía la sesión
del test (commit) y la activity abre SU propia sesión vía ``session_maker``.

- ``create_analysis_run``: fila SYSTEM/RUNNING, idempotencia por ``run_id``
  determinista y espera reintentable ante un run activo AJENO.
- ``mark_analysis_run_failed``: RUNNING ⇒ FAILED; estados terminales no-op.
- ``dispatch_case_event``: outbox + entrega con dispatcher fake (sin HTTP),
  idempotencia aplicativa por (type, case:run, destination) y 0 sin destinos.
"""

from uuid import uuid4

import pytest
from expects import be_none, equal, expect, have_keys, have_length
from sqlalchemy import delete, select
from temporalio.exceptions import ApplicationError

from src.common.application.helpers.webhooks.delivery import WebhookDeliveryResult
from src.common.database.config import get_database_config
from src.common.database.models.processing.workflow_analysis_run import WorkflowAnalysisRunORM
from src.common.database.models.webhook_destination import WebhookDestinationORM
from src.common.database.models.workflow_event import WorkflowEventORM
from src.common.domain.entities.workflows.analysis_run_processing import (
    CreateAnalysisRunForPipelineInput,
    DispatchCaseEventInput,
    MarkAnalysisRunFailedInput,
)
from src.common.domain.enums.webhooks import WebhookEventType, WorkflowEventDeliveryStatus
from src.common.domain.enums.workflow_rules import (
    WorkflowAnalysisRunStatus,
    WorkflowAnalysisRunTrigger,
)
from src.workflows.presentation.workflows.activities.case_phase_activities import (
    ACTIVE_RUN_WAIT_ERROR,
    CaseAnalysisRunActivities,
    DispatchCaseEventActivity,
)


@pytest.fixture
def session_maker():
    return get_database_config().session_maker


@pytest.fixture
def run_activities(session_maker):
    return CaseAnalysisRunActivities(session_maker=session_maker)


class FakeDispatcher:
    """Dispatcher de webhooks que registra entregas sin tocar la red."""

    def __init__(self, delivered: bool = True):
        self.delivered = delivered
        self.calls: list[dict] = []

    async def deliver(self, **kwargs):
        self.calls.append(kwargs)
        return WebhookDeliveryResult(
            delivered=self.delivered,
            attempts=1,
            status_code=200 if self.delivered else 500,
            error=None if self.delivered else "boom",
        )


def _create_input(tenant_orm, workflow_orm, case_orm, run_id=None) -> CreateAnalysisRunForPipelineInput:
    return CreateAnalysisRunForPipelineInput(
        run_id=run_id or uuid4(),
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        case_id=case_orm.uuid,
    )


async def _read_run(session_maker, run_id) -> WorkflowAnalysisRunORM | None:
    async with session_maker() as fresh:
        return (
            await fresh.execute(select(WorkflowAnalysisRunORM).where(WorkflowAnalysisRunORM.uuid == run_id))
        ).scalar_one_or_none()


async def _runs_for_case(session_maker, case_id) -> list[WorkflowAnalysisRunORM]:
    async with session_maker() as fresh:
        return list(
            (
                await fresh.execute(
                    select(WorkflowAnalysisRunORM).where(WorkflowAnalysisRunORM.workflow_case_id == case_id)
                )
            ).scalars()
        )


async def _cleanup_tenant_rows(session_maker, tenant_id) -> None:
    """Borra las filas committeadas por estos tests (runs, eventos, destinos)."""
    async with session_maker() as cleanup:
        await cleanup.execute(delete(WorkflowEventORM).where(WorkflowEventORM.tenant_id == tenant_id))
        await cleanup.execute(delete(WorkflowAnalysisRunORM).where(WorkflowAnalysisRunORM.tenant_id == tenant_id))
        await cleanup.execute(delete(WebhookDestinationORM).where(WebhookDestinationORM.tenant_id == tenant_id))
        await cleanup.commit()


# ─── create_analysis_run ─────────────────────────────────────────────────────


async def test_create_analysis_run__creates_system_running_row(
    run_activities, session_maker, async_session, tenant_orm, workflow_orm, case_orm
):
    # Arrange — committea tenant/workflow/case para la sesión de la activity
    await async_session.commit()
    payload = _create_input(tenant_orm, workflow_orm, case_orm)

    try:
        # Act
        result = await run_activities.create_analysis_run(payload)

        # Assert
        expect(result.created).to(equal(True))
        expect(result.run_id).to(equal(payload.run_id))
        row = await _read_run(session_maker, payload.run_id)
        expect(row.status).to(equal(WorkflowAnalysisRunStatus.RUNNING.value))
        expect(row.trigger).to(equal(WorkflowAnalysisRunTrigger.SYSTEM.value))
        expect(row.triggered_by).to(be_none)
        expect(row.workflow_case_id).to(equal(case_orm.uuid))
    finally:
        await _cleanup_tenant_rows(session_maker, tenant_orm.uuid)


async def test_create_analysis_run__retry_with_same_run_id_is_idempotent(
    run_activities, session_maker, async_session, tenant_orm, workflow_orm, case_orm
):
    # Arrange
    await async_session.commit()
    payload = _create_input(tenant_orm, workflow_orm, case_orm)

    try:
        await run_activities.create_analysis_run(payload)

        # Act — replay de la activity con el MISMO run_id determinista
        retry = await run_activities.create_analysis_run(payload)

        # Assert — encuentra su propia fila: no duplica ni falla
        expect(retry.created).to(equal(False))
        expect(retry.run_id).to(equal(payload.run_id))
        expect(await _runs_for_case(session_maker, case_orm.uuid)).to(have_length(1))
    finally:
        await _cleanup_tenant_rows(session_maker, tenant_orm.uuid)


async def test_create_analysis_run__foreign_active_run_raises_retryable_wait(
    run_activities, session_maker, async_session, tenant_orm, workflow_orm, case_orm
):
    # Arrange — otro upload ya dejó un run RUNNING para el mismo caso
    await async_session.commit()
    foreign = _create_input(tenant_orm, workflow_orm, case_orm)

    try:
        await run_activities.create_analysis_run(foreign)

        # Act / Assert — REINTENTABLE: el retry policy de la fase es la espera
        with pytest.raises(ApplicationError) as exc_info:
            await run_activities.create_analysis_run(_create_input(tenant_orm, workflow_orm, case_orm))

        expect(exc_info.value.type).to(equal(ACTIVE_RUN_WAIT_ERROR))
        expect(exc_info.value.non_retryable).to(equal(False))
        expect(await _runs_for_case(session_maker, case_orm.uuid)).to(have_length(1))
    finally:
        await _cleanup_tenant_rows(session_maker, tenant_orm.uuid)


# ─── mark_analysis_run_failed ────────────────────────────────────────────────


async def test_mark_analysis_run_failed__running_run_transitions_to_failed(
    run_activities, session_maker, async_session, tenant_orm, workflow_orm, case_orm
):
    # Arrange
    await async_session.commit()
    payload = _create_input(tenant_orm, workflow_orm, case_orm)

    try:
        await run_activities.create_analysis_run(payload)

        # Act
        await run_activities.mark_analysis_run_failed(
            MarkAnalysisRunFailedInput(run_id=payload.run_id, tenant_id=tenant_orm.uuid, error="child died")
        )

        # Assert
        row = await _read_run(session_maker, payload.run_id)
        expect(row.status).to(equal(WorkflowAnalysisRunStatus.FAILED.value))
        expect(row.error).to(equal("child died"))
        expect(row.completed_at is not None).to(equal(True))
    finally:
        await _cleanup_tenant_rows(session_maker, tenant_orm.uuid)


async def test_mark_analysis_run_failed__terminal_run_is_noop(
    run_activities, session_maker, async_session, tenant_orm, workflow_orm, case_orm
):
    # Arrange — el child ya cerró su fila como COMPLETED
    await async_session.commit()
    payload = _create_input(tenant_orm, workflow_orm, case_orm)

    try:
        await run_activities.create_analysis_run(payload)
        async with session_maker() as setup:
            row = (
                await setup.execute(
                    select(WorkflowAnalysisRunORM).where(WorkflowAnalysisRunORM.uuid == payload.run_id)
                )
            ).scalar_one()
            row.status = WorkflowAnalysisRunStatus.COMPLETED.value
            await setup.commit()

        # Act — la red de seguridad llega tarde: no debe pisar el estado terminal
        await run_activities.mark_analysis_run_failed(
            MarkAnalysisRunFailedInput(run_id=payload.run_id, tenant_id=tenant_orm.uuid, error="too late")
        )

        # Assert
        refreshed = await _read_run(session_maker, payload.run_id)
        expect(refreshed.status).to(equal(WorkflowAnalysisRunStatus.COMPLETED.value))
        expect(refreshed.error).to(be_none)
    finally:
        await _cleanup_tenant_rows(session_maker, tenant_orm.uuid)


async def test_mark_analysis_run_failed__missing_run_is_noop(
    run_activities, session_maker, async_session, tenant_orm
):
    # Arrange
    await async_session.commit()

    # Act / Assert — no explota (replay tras un borrado, p. ej.)
    await run_activities.mark_analysis_run_failed(
        MarkAnalysisRunFailedInput(run_id=uuid4(), tenant_id=tenant_orm.uuid, error="ghost")
    )


# ─── dispatch_case_event ─────────────────────────────────────────────────────


def _seed_destination(async_session, tenant_orm, workflow_orm, events: list[str]) -> WebhookDestinationORM:
    destination = WebhookDestinationORM(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        name="Case events sink",
        url="https://receiver.test/hooks/case",
        secret="whsec_testsecret",
        enabled=True,
        subscribed_events=events,
    )
    async_session.add(destination)
    return destination


def _dispatch_input(tenant_orm, workflow_orm, case_orm, run_id, event_type, error=None) -> DispatchCaseEventInput:
    return DispatchCaseEventInput(
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        case_id=case_orm.uuid,
        run_id=run_id,
        event_type=event_type,
        error=error,
    )


async def _events_for_tenant(session_maker, tenant_id) -> list[WorkflowEventORM]:
    async with session_maker() as fresh:
        return list(
            (await fresh.execute(select(WorkflowEventORM).where(WorkflowEventORM.tenant_id == tenant_id))).scalars()
        )


async def test_dispatch_case_event__subscribed_destination_gets_enveloped_event(
    session_maker, async_session, tenant_orm, workflow_orm, case_orm
):
    # Arrange
    _seed_destination(async_session, tenant_orm, workflow_orm, [WebhookEventType.CASE_OUTPUT_READY.value])
    await async_session.commit()
    dispatcher = FakeDispatcher(delivered=True)
    activity = DispatchCaseEventActivity(session_maker=session_maker, dispatcher=dispatcher)
    run_id = uuid4()

    try:
        # Act
        dispatched = await activity.dispatch_case_event(
            _dispatch_input(tenant_orm, workflow_orm, case_orm, run_id, WebhookEventType.CASE_OUTPUT_READY.value)
        )

        # Assert — un destino entregado, con la firma del dispatcher fake
        expect(dispatched).to(equal(1))
        expect(dispatcher.calls).to(have_length(1))
        expect(dispatcher.calls[0]["url"]).to(equal("https://receiver.test/hooks/case"))

        # Assert — outbox: WorkflowEvent con clave estable caso+run y envelope E2
        events = await _events_for_tenant(session_maker, tenant_orm.uuid)
        expect(events).to(have_length(1))
        event = events[0]
        expect(event.idempotency_key).to(equal(f"case:{case_orm.uuid}:run:{run_id}"))
        expect(event.event_type).to(equal(WebhookEventType.CASE_OUTPUT_READY.value))
        expect(event.document_id).to(be_none)
        expect(event.delivery_status).to(equal(WorkflowEventDeliveryStatus.DELIVERED.value))
        expect(event.payload).to(have_keys("eventId", "eventType", "createdAt", "data"))
        expect(event.payload["eventType"]).to(equal(WebhookEventType.CASE_OUTPUT_READY.value))
        expect(event.payload["data"]).to(
            have_keys(
                caseId=str(case_orm.uuid),
                workflowId=str(workflow_orm.uuid),
                runId=str(run_id),
            )
        )
    finally:
        await _cleanup_tenant_rows(session_maker, tenant_orm.uuid)


async def test_dispatch_case_event__case_failed_carries_error_in_payload(
    session_maker, async_session, tenant_orm, workflow_orm, case_orm
):
    # Arrange
    _seed_destination(async_session, tenant_orm, workflow_orm, [WebhookEventType.CASE_FAILED.value])
    await async_session.commit()
    dispatcher = FakeDispatcher(delivered=True)
    activity = DispatchCaseEventActivity(session_maker=session_maker, dispatcher=dispatcher)

    try:
        # Act
        dispatched = await activity.dispatch_case_event(
            _dispatch_input(
                tenant_orm,
                workflow_orm,
                case_orm,
                None,
                WebhookEventType.CASE_FAILED.value,
                error={"code": "pipeline.analyze_failed", "message": "regla 7 explotó"},
            )
        )

        # Assert
        expect(dispatched).to(equal(1))
        events = await _events_for_tenant(session_maker, tenant_orm.uuid)
        expect(events).to(have_length(1))
        payload = events[0].payload
        expect(payload["eventType"]).to(equal(WebhookEventType.CASE_FAILED.value))
        expect(payload["data"]["error"]).to(
            equal({"code": "pipeline.analyze_failed", "message": "regla 7 explotó"})
        )
        expect(payload["data"]).to(have_keys("failedAt"))
        expect(events[0].idempotency_key).to(equal(f"case:{case_orm.uuid}:run:none"))
    finally:
        await _cleanup_tenant_rows(session_maker, tenant_orm.uuid)


async def test_dispatch_case_event__delivered_event_is_not_recreated(
    session_maker, async_session, tenant_orm, workflow_orm, case_orm
):
    # Arrange — el evento de un retry anterior ya quedó DELIVERED en el outbox
    destination = _seed_destination(
        async_session, tenant_orm, workflow_orm, [WebhookEventType.CASE_OUTPUT_READY.value]
    )
    run_id = uuid4()
    job_key = f"case:{case_orm.uuid}:run:{run_id}"
    async_session.add(
        WorkflowEventORM(
            uuid=uuid4(),
            tenant_id=tenant_orm.uuid,
            event_id=f"evt_{uuid4()}",
            event_type=WebhookEventType.CASE_OUTPUT_READY.value,
            workflow_id=workflow_orm.uuid,
            processing_job_id=None,
            document_id=None,
            destination_id=destination.uuid,
            idempotency_key=job_key,
            document_status="EXTRACTED",
            payload={"eventId": "evt_prev", "eventType": WebhookEventType.CASE_OUTPUT_READY.value},
            delivery_status=WorkflowEventDeliveryStatus.DELIVERED.value,
        )
    )
    await async_session.commit()
    dispatcher = FakeDispatcher(delivered=True)
    activity = DispatchCaseEventActivity(session_maker=session_maker, dispatcher=dispatcher)

    try:
        # Act — replay de la activity para el mismo (type, case:run, destination)
        dispatched = await activity.dispatch_case_event(
            _dispatch_input(tenant_orm, workflow_orm, case_orm, run_id, WebhookEventType.CASE_OUTPUT_READY.value)
        )

        # Assert — idempotencia aplicativa: ni re-crea ni re-entrega
        expect(dispatched).to(equal(0))
        expect(dispatcher.calls).to(have_length(0))
        expect(await _events_for_tenant(session_maker, tenant_orm.uuid)).to(have_length(1))
    finally:
        await _cleanup_tenant_rows(session_maker, tenant_orm.uuid)


async def test_dispatch_case_event__no_subscribed_destinations_returns_zero(
    session_maker, async_session, tenant_orm, workflow_orm, case_orm
):
    # Arrange — hay destino pero suscrito a OTRO evento
    _seed_destination(async_session, tenant_orm, workflow_orm, [WebhookEventType.CASE_FAILED.value])
    await async_session.commit()
    dispatcher = FakeDispatcher(delivered=True)
    activity = DispatchCaseEventActivity(session_maker=session_maker, dispatcher=dispatcher)

    try:
        # Act
        dispatched = await activity.dispatch_case_event(
            _dispatch_input(tenant_orm, workflow_orm, case_orm, uuid4(), WebhookEventType.CASE_OUTPUT_READY.value)
        )

        # Assert — 0 entregas, 0 filas en el outbox, 0 HTTP
        expect(dispatched).to(equal(0))
        expect(dispatcher.calls).to(have_length(0))
        expect(await _events_for_tenant(session_maker, tenant_orm.uuid)).to(have_length(0))
    finally:
        await _cleanup_tenant_rows(session_maker, tenant_orm.uuid)
