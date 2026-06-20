"""Scheduled replay of pending/failed webhook deliveries (spec §4.8 / §5.19).

Re-attempts ``PENDING``/``FAILED`` events with exponential backoff up to **8
attempts** and a **24h** window, after which they are left ``FAILED`` for good.
Marks ``DELIVERING`` while attempting to avoid racing the inline dispatch.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.common.application.logging import get_logger
from src.common.domain.enums.webhooks import WorkflowEventDeliveryStatus
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.workflow_event import WorkflowEvent
from src.workflows.application.processing_jobs.webhook_dispatcher import WorkflowWebhookDispatcher
from src.workflows.domain.repositories.webhook_destination import WebhookDestinationRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_event import WorkflowEventRepository

logger = get_logger(__name__)

MAX_ATTEMPTS = 8  # decisión §5.19
MAX_AGE_HOURS = 24  # decisión §5.19


@dataclass
class RetryPendingWorkflowEvents(UseCase):
    workflow_event_repository: WorkflowEventRepository
    workflow_repository: WorkflowRepository
    webhook_destination_repository: WebhookDestinationRepository
    dispatcher: WorkflowWebhookDispatcher
    now: datetime
    max_attempts: int = MAX_ATTEMPTS
    max_age_hours: int = MAX_AGE_HOURS
    batch_size: int = 100

    async def execute(self) -> int:
        candidates = await self.workflow_event_repository.list_for_retry(limit=self.batch_size)
        cutoff = self.now - timedelta(hours=self.max_age_hours)
        retried = 0

        for event in candidates:
            exhausted = event.attempts >= self.max_attempts
            expired = event.created_at is not None and event.created_at < cutoff
            if exhausted or expired:
                if event.delivery_status != WorkflowEventDeliveryStatus.FAILED:
                    event.delivery_status = WorkflowEventDeliveryStatus.FAILED
                    event.last_error = event.last_error or "retry window/attempts exhausted"
                    await self.workflow_event_repository.update(event)
                continue

            url, secret = await self._resolve_target(event)
            if not url or not secret:
                continue

            try:
                await self._redeliver(url, secret, event)
                retried += 1
            except Exception as exc:
                logger.warning("retry_pending.failed", event_id=event.event_id, error=str(exc))

        logger.info("retry_pending_workflow_events.batch", candidates=len(candidates), retried=retried)
        return retried

    async def _resolve_target(self, event: WorkflowEvent) -> tuple[str | None, str | None]:
        """Deliver to the event's destination (its current URL/secret); fall back
        to the legacy per-workflow webhook config for pre-destination events."""
        if event.destination_id is not None:
            destination = await self.webhook_destination_repository.find_by_id(
                event.destination_id, event.tenant_id
            )
            if destination is not None:
                return destination.url, destination.secret

        workflow = await self.workflow_repository.find_by_id(event.workflow_id, event.tenant_id)
        if workflow is None:
            return None, None
        return workflow.webhook_url, workflow.webhook_secret

    async def _redeliver(self, url: str, secret: str, event: WorkflowEvent) -> None:
        body = json.dumps(event.payload, separators=(",", ":"), ensure_ascii=False)
        timestamp = int(self.now.timestamp())

        event.delivery_status = WorkflowEventDeliveryStatus.DELIVERING
        event.last_attempt_at = datetime.now(UTC)
        await self.workflow_event_repository.update(event)

        result = await self.dispatcher.deliver(
            url=url,
            secret=secret,
            event_id=event.event_id,
            body=body,
            timestamp=timestamp,
        )

        event.attempts += max(result.attempts, 1)
        event.response_status = result.status_code
        if result.delivered:
            event.delivery_status = WorkflowEventDeliveryStatus.DELIVERED
            event.delivered_at = datetime.now(UTC)
            event.last_error = None
        else:
            event.delivery_status = WorkflowEventDeliveryStatus.FAILED
            event.last_error = result.error
        await self.workflow_event_repository.update(event)
