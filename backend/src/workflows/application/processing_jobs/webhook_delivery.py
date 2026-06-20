"""Shared outbound-webhook delivery (F3).

Signing + HTTP delivery + delivery-status bookkeeping for one persisted
``WorkflowEvent``. Extracted so both the processing-job dispatcher and the
analysis-run summary dispatcher (decision W1) deliver identically — one source of
truth for the ``DELIVERING → DELIVERED/FAILED`` transitions.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from src.common.domain.enums.webhooks import WorkflowEventDeliveryStatus
from src.common.domain.models.workflow_event import WorkflowEvent
from src.workflows.application.processing_jobs.webhook_dispatcher import (
    WorkflowWebhookDispatcher,
)
from src.workflows.domain.repositories.workflow_event import WorkflowEventRepository


async def deliver_event(
    *,
    dispatcher: WorkflowWebhookDispatcher,
    event_repository: WorkflowEventRepository,
    url: str,
    secret: str | None,
    event: WorkflowEvent,
) -> None:
    """Sign + POST ``event`` to ``url``, persisting each delivery transition."""
    if not secret:
        event.delivery_status = WorkflowEventDeliveryStatus.FAILED
        event.last_error = "destination has no signing secret"
        await event_repository.update(event)
        return

    body = json.dumps(event.payload, separators=(",", ":"), ensure_ascii=False)
    timestamp = int(datetime.now(UTC).timestamp())

    event.delivery_status = WorkflowEventDeliveryStatus.DELIVERING
    event.last_attempt_at = datetime.now(UTC)
    await event_repository.update(event)

    result = await dispatcher.deliver(
        url=url,
        secret=secret,
        event_id=event.event_id,
        body=body,
        timestamp=timestamp,
    )

    event.attempts += result.attempts
    event.response_status = result.status_code
    if result.delivered:
        event.delivery_status = WorkflowEventDeliveryStatus.DELIVERED
        event.delivered_at = datetime.now(UTC)
        event.last_error = None
    else:
        event.delivery_status = WorkflowEventDeliveryStatus.FAILED
        event.last_error = result.error
    await event_repository.update(event)
