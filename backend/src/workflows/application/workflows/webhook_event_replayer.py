import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.common.application.helpers.webhooks.delivery import deliver_webhook
from src.common.domain.enums.webhooks import WorkflowEventDeliveryStatus
from src.common.domain.exceptions.processing import (
    WorkflowEventNotFoundError,
    WorkflowWebhookNotConfiguredError,
)
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.workflow_event import WorkflowEvent
from src.workflows.domain.repositories.webhook_destination import WebhookDestinationRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_event import WorkflowEventRepository


@dataclass
class WorkflowEventReplayer(UseCase):
    """Manually re-deliver a persisted webhook event (spec §10, distinct from §4.8 job).

    Re-delivers to the event's destination (its current URL/secret). Falls back to
    the legacy per-workflow webhook config for events created before destinations.
    """

    workflow_id: UUID
    event_uuid: UUID
    tenant_id: UUID
    workflow_event_repository: WorkflowEventRepository
    workflow_repository: WorkflowRepository
    webhook_destination_repository: WebhookDestinationRepository

    async def execute(self) -> WorkflowEvent:
        event = await self.workflow_event_repository.find_by_id(self.event_uuid, self.tenant_id)
        if event is None or event.workflow_id != self.workflow_id:
            raise WorkflowEventNotFoundError(str(self.event_uuid))

        url, secret = await self._resolve_target(event)
        if not url or not secret:
            raise WorkflowWebhookNotConfiguredError

        # Re-serialize the immutable payload snapshot; sign over the exact bytes sent.
        body = json.dumps(event.payload, separators=(",", ":"), ensure_ascii=False)
        timestamp = int(datetime.now(UTC).timestamp())

        event.delivery_status = WorkflowEventDeliveryStatus.DELIVERING
        event.last_attempt_at = datetime.now(UTC)
        await self.workflow_event_repository.update(event)

        result = await deliver_webhook(
            url=url,
            body=body,
            secret=secret,
            event_id=event.event_id,
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

        return await self.workflow_event_repository.update(event)

    async def _resolve_target(self, event: WorkflowEvent) -> tuple[str | None, str | None]:
        """Return the (url, secret) to deliver to: the event's destination first,
        else the legacy per-workflow webhook config."""
        if event.destination_id is not None:
            destination = await self.webhook_destination_repository.find_by_id(
                event.destination_id, self.tenant_id
            )
            if destination is not None:
                return destination.url, destination.secret

        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if workflow is None:
            return None, None
        return workflow.webhook_url, workflow.webhook_secret
