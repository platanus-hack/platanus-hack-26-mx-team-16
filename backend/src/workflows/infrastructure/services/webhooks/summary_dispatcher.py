"""Real ``SummaryWebhookDispatcher`` — emits ``analysis_run.completed`` (W1).

When a ``WorkflowAnalysisRun`` finalises, fan out one signed delivery per enabled
``workflow_destinations`` row subscribed to ``analysis_run.completed``. The result
payload IS the pipeline's ``output_schema``-shaped synthesis (decision W1), not a
per-case event. Reuses the standard webhook persistence (``WorkflowEvent``) and
the shared :func:`deliver_event` so STANDARD and ANALYSIS deliver identically.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.common.application.logging import get_logger
from src.common.domain.enums.run_summary import NarrativeStatus
from src.common.domain.enums.webhooks import WebhookEventType, WorkflowEventDeliveryStatus
from src.common.domain.models.processing.workflow_analysis_run_summary import (
    WorkflowAnalysisRunSummary,
)
from src.common.domain.models.workflow_event import WorkflowEvent
from src.workflows.application.processing_jobs.webhook_delivery import deliver_event
from src.workflows.application.processing_jobs.webhook_dispatcher import (
    WorkflowWebhookDispatcher,
)
from src.workflows.infrastructure.repositories.sql_webhook_destination import (
    SQLWebhookDestinationRepository,
)
from src.workflows.infrastructure.repositories.sql_workflow_analysis_run import (
    SQLWorkflowAnalysisRunRepository,
)
from src.workflows.infrastructure.repositories.sql_workflow_event import (
    SQLWorkflowEventRepository,
)
from src.workflows.infrastructure.services.webhooks.http_dispatcher import (
    HttpWorkflowWebhookDispatcher,
)

logger = get_logger(__name__)

_EVENT_TYPE = WebhookEventType.ANALYSIS_RUN_COMPLETED


def build_analysis_run_payload(
    *, event_id: str, run_id: UUID, workflow_id: UUID, summary: WorkflowAnalysisRunSummary
) -> dict:
    """Standard-Webhooks envelope for ``analysis_run.completed`` (decision W1)."""
    return {
        "eventId": event_id,
        "eventType": _EVENT_TYPE.value,
        "createdAt": datetime.now(UTC).isoformat(),
        "data": {
            "runId": str(run_id),
            "workflowId": str(workflow_id),
            "verdict": summary.verdict.value,
            "confidenceScore": summary.confidence_score,
            "narrativeStatus": summary.narrative_status.value,
            # The result payload is the pipeline output_schema-shaped synthesis.
            "output": summary.output,
            "outputSchema": summary.output_schema_snapshot,
        },
    }


class WorkflowSummaryWebhookDispatcher:
    def __init__(
        self,
        session_maker: async_sessionmaker,
        dispatcher: WorkflowWebhookDispatcher | None = None,
    ) -> None:
        self._session_maker = session_maker
        self._dispatcher = dispatcher or HttpWorkflowWebhookDispatcher()

    async def dispatch(self, *, run_id: UUID, summary: WorkflowAnalysisRunSummary) -> None:
        if summary.narrative_status != NarrativeStatus.COMPLETED:
            return
        tenant_id = summary.tenant_id
        async with self._session_maker() as session:
            run = await SQLWorkflowAnalysisRunRepository(session=session).find_by_id(run_id, tenant_id)
            if run is None:
                logger.warning("analysis_webhook.run_not_found", run_id=str(run_id))
                return
            destinations = await SQLWebhookDestinationRepository(session=session).list_enabled_for_event(
                run.workflow_id, tenant_id, _EVENT_TYPE
            )
            if not destinations:
                return
            event_repo = SQLWorkflowEventRepository(session=session)
            for destination in destinations:
                try:
                    await self._dispatch_one(event_repo, destination, run_id, run.workflow_id, tenant_id, summary)
                except Exception as exc:  # fire-and-forget per destination
                    logger.warning(
                        "analysis_webhook.dispatch_failed",
                        run_id=str(run_id),
                        destination_id=str(destination.uuid),
                        error=str(exc),
                    )

    async def _dispatch_one(self, event_repo, destination, run_id, workflow_id, tenant_id, summary) -> None:
        existing = await event_repo.find_by_unique_destination(None, _EVENT_TYPE, str(run_id), destination.uuid)
        if existing is not None and existing.delivery_status == WorkflowEventDeliveryStatus.DELIVERED:
            return  # already delivered to this destination for this run (idempotent)

        if existing is None:
            payload = build_analysis_run_payload(
                event_id=f"evt_{uuid4()}",
                run_id=run_id,
                workflow_id=workflow_id,
                summary=summary,
            )
            event = await event_repo.create(
                WorkflowEvent(
                    uuid=uuid4(),
                    tenant_id=tenant_id,
                    event_id=payload["eventId"],
                    event_type=_EVENT_TYPE,
                    workflow_id=workflow_id,
                    processing_job_id=None,
                    document_id=None,
                    destination_id=destination.uuid,
                    idempotency_key=str(run_id),
                    document_status=summary.verdict.value,
                    payload=payload,
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
