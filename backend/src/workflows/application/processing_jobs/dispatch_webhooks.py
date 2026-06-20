"""Use case: dispatch outbound webhooks for a finalized document set (spec §4.6).

Loads the workflow/set/terminal documents, applies the gate (§5.15), builds one
idempotent ``WorkflowEvent`` per document (§4.1), and delegates delivery to the
injected dispatcher. Fire-and-forget (§5.16): per-document failures are caught
and logged; the use case never raises so the Temporal run cannot fail.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from src.common.application.logging import get_logger
from src.common.domain.enums.webhooks import WebhookEventType, WorkflowEventDeliveryStatus
from src.common.domain.enums.workflows import WorkflowDocumentStatus
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow import Workflow
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.webhook_destination import WebhookDestination
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.common.domain.models.workflow_event import WorkflowEvent
from src.workflows.application.processing_jobs.webhook_delivery import deliver_event
from src.workflows.application.processing_jobs.webhook_dispatcher import WorkflowWebhookDispatcher
from src.workflows.application.processing_jobs.webhook_payload import build_event_payload
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.webhook_destination import WebhookDestinationRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository
from src.workflows.domain.repositories.workflow_processing_job_repository import (
    WorkflowProcessingJobRepository,
)
from src.workflows.domain.repositories.workflow_event import WorkflowEventRepository

if TYPE_CHECKING:
    from uuid import UUID

logger = get_logger(__name__)

_TERMINAL_STATUSES = (WorkflowDocumentStatus.EXTRACTED, WorkflowDocumentStatus.ERROR)
_EVENT_TYPE_BY_STATUS = {
    WorkflowDocumentStatus.EXTRACTED: WebhookEventType.DOCUMENT_EXTRACTED,
    WorkflowDocumentStatus.ERROR: WebhookEventType.DOCUMENT_FAILED,
}


@dataclass
class DispatchProcessingJobWebhooks(UseCase):
    processing_job_id: UUID
    workflow_id: UUID
    run_id: str
    final_status: str
    workflow_repository: WorkflowRepository
    processing_job_repository: WorkflowProcessingJobRepository
    document_repository: WorkflowDocumentRepository
    document_type_repository: DocumentTypeRepository
    workflow_event_repository: WorkflowEventRepository
    webhook_destination_repository: WebhookDestinationRepository
    dispatcher: WorkflowWebhookDispatcher
    # phases-config · finalize.webhook_projection: subset de campos del `extraction`.
    webhook_projection: list[str] | None = None

    async def execute(self) -> None:
        processing_job = await self.processing_job_repository.find_by_uuid(self.processing_job_id)
        if processing_job is None:
            logger.warning("workflow_webhook.set_not_found", processing_job_id=str(self.processing_job_id))
            return
        tenant_id = processing_job.tenant_id

        workflow = await self.workflow_repository.find_by_id(self.workflow_id, tenant_id)
        if workflow is None:
            return

        documents = await self.document_repository.list_by_processing_job(self.processing_job_id)
        terminal = [doc for doc in documents if doc.status in _TERMINAL_STATUSES]
        if not terminal:
            return

        type_ids = list({doc.document_type_id for doc in terminal if doc.document_type_id})
        type_names = await self.document_type_repository.find_by_ids(type_ids, tenant_id) if type_ids else {}

        for document in terminal:
            event_type = _EVENT_TYPE_BY_STATUS[document.status]
            # Fan out: one delivery per enabled destination subscribed to this
            # event type (§4.6). No destinations → nothing is created.
            destinations = await self.webhook_destination_repository.list_enabled_for_event(
                self.workflow_id, tenant_id, event_type
            )
            for destination in destinations:
                try:
                    await self._dispatch_one(
                        workflow,
                        processing_job,
                        document,
                        tenant_id,
                        type_names,
                        event_type,
                        destination,
                    )
                except Exception as exc:
                    logger.warning(
                        "workflow_webhook.document_dispatch_failed",
                        document_id=str(document.uuid),
                        destination_id=str(destination.uuid),
                        error=str(exc),
                    )

    async def _dispatch_one(
        self,
        workflow: Workflow,
        processing_job: WorkflowProcessingJob,
        document: WorkflowDocument,
        tenant_id: UUID,
        type_names: dict[UUID, str],
        event_type: WebhookEventType,
        destination: WebhookDestination,
    ) -> None:
        existing = await self.workflow_event_repository.find_by_unique_destination(
            document.uuid, event_type, self.run_id, destination.uuid
        )
        if existing is not None and existing.delivery_status == WorkflowEventDeliveryStatus.DELIVERED:
            return  # already delivered to this destination for this run (idempotent)

        if existing is None:
            payload = build_event_payload(
                workflow=workflow,
                processing_job=processing_job,
                document=document,
                document_type_name=type_names.get(document.document_type_id),
                event_type=event_type,
                event_id=f"evt_{uuid4()}",
                final_status=self.final_status,
                field_projection=self.webhook_projection,
            )
            event = WorkflowEvent(
                uuid=uuid4(),
                tenant_id=tenant_id,
                event_id=payload["eventId"],
                event_type=event_type,
                workflow_id=workflow.uuid,
                processing_job_id=processing_job.uuid,
                document_id=document.uuid,
                destination_id=destination.uuid,
                idempotency_key=self.run_id,
                document_status=document.status.value,
                payload=payload,
                delivery_status=WorkflowEventDeliveryStatus.PENDING,
            )
            event = await self.workflow_event_repository.create(event)
        else:
            event = existing

        await self._deliver_to(destination.url, destination.secret, event)

    async def _deliver_to(self, url: str, secret: str | None, event: WorkflowEvent) -> None:
        await deliver_event(
            dispatcher=self.dispatcher,
            event_repository=self.workflow_event_repository,
            url=url,
            secret=secret,
            event=event,
        )
