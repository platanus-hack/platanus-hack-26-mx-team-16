"""CaseEventDispatcher — eventos ``case.*`` al outbox (E2 deliver · E3 created).

Lógica compartida entre la activity Temporal ``dispatch_case_event`` (fase
deliver) y los endpoints M2M (``case.created`` al crear caso por API): encola
``WorkflowEvent`` por destino suscrito (idempotencia aplicativa por
``(type, case:run, destination)`` — la unique de BD no aplica con
``document_id`` NULL) y entrega firmado vía ``deliver_event``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.common.application.logging import get_logger
from src.common.domain.entities.workflows.analysis_run_processing import (
    DispatchCaseEventInput,
)
from src.common.domain.enums.webhooks import WebhookEventType, WorkflowEventDeliveryStatus
from src.common.domain.models.workflow_event import WorkflowEvent

logger = get_logger(__name__)


def build_case_event_payload(*, event_id: str, data: DispatchCaseEventInput, summary) -> dict:
    """Standard-Webhooks envelope para los checkpoints del caso."""
    body: dict = {
        "caseId": str(data.case_id),
        "workflowId": str(data.workflow_id),
        "runId": str(data.run_id) if data.run_id else None,
    }
    if data.event_type == WebhookEventType.CASE_OUTPUT_READY.value and summary is not None:
        output = summary.output
        # phases-config · deliver.payload_projection: recorta el `output` al
        # subconjunto pedido. None ⇒ output completo (comportamiento de hoy).
        if data.payload_projection is not None and isinstance(output, dict):
            allow = set(data.payload_projection)
            output = {k: v for k, v in output.items() if k in allow}
        body.update(
            {
                "verdict": summary.verdict.value if summary.verdict else None,
                "confidenceScore": summary.confidence_score,
                "narrativeStatus": summary.narrative_status.value if summary.narrative_status else None,
                "output": output,
                "outputSchema": summary.output_schema_snapshot,
            }
        )
    if data.event_type == WebhookEventType.CASE_FAILED.value:
        body["error"] = data.error or {"code": "case.failed", "message": "case pipeline failed"}
        body["failedAt"] = datetime.now(UTC).isoformat()
    if data.event_type == WebhookEventType.CASE_CREATED.value:
        # `error` se reutiliza como bolsa de metadatos del creador (external_ref…).
        body.update(data.error or {})
    if data.event_type in (
        WebhookEventType.CASE_NEEDS_REVIEW.value,
        WebhookEventType.CASE_NEEDS_CLARIFICATION.value,
        WebhookEventType.CASE_REVIEW_COMPLETED.value,
    ):
        # E4/E5: el payload rico viene de la fase (clarification request §4.5 /
        # contexto de aprobación / stages con outcome) — taskId/stage/items/….
        body.update(data.payload or {})
        if data.task_id is not None:
            body.setdefault("taskId", str(data.task_id))
    return {
        "eventId": event_id,
        "eventType": data.event_type,
        "createdAt": datetime.now(UTC).isoformat(),
        "data": body,
    }


def select_destinations(destinations: list, channels: list[str] | None) -> list:
    """phases-config · deliver.channels: intersecta el allowlist de la fase con
    los destinos suscritos (match por uuid string o name). ``None`` ⇒ todos los
    enabled+suscritos (comportamiento de hoy). Lista vacía ⇒ ninguno (entrega a
    nadie — intencional, distinto de None)."""
    if channels is None:
        return destinations
    allow = set(channels)
    return [d for d in destinations if str(d.uuid) in allow or getattr(d, "name", None) in allow]


def _status_label(event_type: WebhookEventType, summary) -> str:
    # OJO (gotcha E2): WorkflowEvent.document_status es NOT NULL str — labels.
    if event_type == WebhookEventType.CASE_NEEDS_REVIEW:
        return "REVIEW"
    if event_type == WebhookEventType.CASE_NEEDS_CLARIFICATION:
        return "CLARIFICATION"
    if event_type == WebhookEventType.CASE_REVIEW_COMPLETED:
        return "REVIEW_COMPLETED"
    if summary is not None and summary.verdict:
        return summary.verdict.value
    if event_type == WebhookEventType.CASE_FAILED:
        return "FAILED"
    if event_type == WebhookEventType.CASE_CREATED:
        return "CREATED"
    return "READY"


class CaseEventDispatcher:
    """Encola + entrega un evento ``case.*`` a los destinos suscritos."""

    def __init__(self, session_maker: async_sessionmaker, dispatcher=None) -> None:
        from src.workflows.infrastructure.services.webhooks.http_dispatcher import (
            HttpWorkflowWebhookDispatcher,
        )

        self._session_maker = session_maker
        self._dispatcher = dispatcher or HttpWorkflowWebhookDispatcher()

    async def dispatch(self, data: DispatchCaseEventInput) -> int:
        async with self._session_maker() as session:
            return await self.dispatch_with_session(session, data)

    async def dispatch_with_session(self, session: AsyncSession, data: DispatchCaseEventInput) -> int:
        from src.workflows.application.processing_jobs.webhook_delivery import deliver_event
        from src.workflows.infrastructure.repositories.sql_run_summary import (
            SQLWorkflowAnalysisRunSummaryRepository,
        )
        from src.workflows.infrastructure.repositories.sql_webhook_destination import (
            SQLWebhookDestinationRepository,
        )
        from src.workflows.infrastructure.repositories.sql_workflow_event import (
            SQLWorkflowEventRepository,
        )

        data = DispatchCaseEventInput.model_validate(data)
        event_type = WebhookEventType(data.event_type)
        # E4: los eventos de pausa son idempotentes por (case, task) — un mismo
        # task_key reabierto en replay no re-entrega.
        if data.task_id is not None:
            job_key = f"case:{data.case_id}:task:{data.task_id}"
        else:
            job_key = f"case:{data.case_id}:run:{data.run_id or 'none'}"

        summary = None
        if data.run_id is not None:
            summary = await SQLWorkflowAnalysisRunSummaryRepository(session=session).find_by_run(
                data.run_id, data.tenant_id
            )

        destinations = await SQLWebhookDestinationRepository(session=session).list_enabled_for_event(
            data.workflow_id, data.tenant_id, event_type
        )
        # phases-config · deliver.channels: allowlist de la fase ∩ destinos suscritos.
        destinations = select_destinations(destinations, data.channels)
        if not destinations:
            logger.info(
                "case_event.no_destinations",
                case_id=str(data.case_id),
                event_type=data.event_type,
            )
            return 0

        event_repo = SQLWorkflowEventRepository(session=session)
        dispatched = 0
        for destination in destinations:
            try:
                existing = await event_repo.find_by_unique_destination(None, event_type, job_key, destination.uuid)
                if existing is not None and existing.delivery_status == WorkflowEventDeliveryStatus.DELIVERED:
                    continue
                if existing is None:
                    payload_dict = build_case_event_payload(event_id=f"evt_{uuid4()}", data=data, summary=summary)
                    event = await event_repo.create(
                        WorkflowEvent(
                            uuid=uuid4(),
                            tenant_id=data.tenant_id,
                            event_id=payload_dict["eventId"],
                            event_type=event_type,
                            workflow_id=data.workflow_id,
                            processing_job_id=None,
                            document_id=None,
                            destination_id=destination.uuid,
                            idempotency_key=job_key,
                            document_status=_status_label(event_type, summary),
                            payload=payload_dict,
                            delivery_status=WorkflowEventDeliveryStatus.PENDING,
                        )
                    )
                else:
                    event = existing
                await deliver_event(
                    dispatcher=self._dispatcher,
                    event_repository=event_repo,
                    url=destination.url,
                    secret=destination.secret,
                    event=event,
                )
                dispatched += 1
            except Exception as exc:  # fire-and-forget por destino (patrón W1)
                logger.warning(
                    "case_event.dispatch_failed",
                    case_id=str(data.case_id),
                    destination_id=str(destination.uuid),
                    error=str(exc),
                )
        return dispatched
