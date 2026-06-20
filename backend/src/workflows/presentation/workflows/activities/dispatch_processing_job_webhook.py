"""Temporal activity that dispatches outbound webhooks for a finalized set.

Runs OUTSIDE the workflow sandbox (I/O boundary, spec §4.6). Re-loads everything
from DB and delegates to :class:`DispatchProcessingJobWebhooks`. Fire-and-forget
(§5.16): all exceptions are swallowed so a delivery problem never fails the run.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio import activity

from src.common.application.logging import get_logger
from src.workflows.application.processing_jobs.dispatch_webhooks import DispatchProcessingJobWebhooks
from src.workflows.application.processing_jobs.webhook_dispatcher import (
    NoopWorkflowWebhookDispatcher,
    WorkflowWebhookDispatcher,
)
from src.workflows.infrastructure.repositories.sql_document_repository import (
    SQLWorkflowDocumentRepository,
)
from src.workflows.infrastructure.repositories.sql_document_type import SQLDocumentTypeRepository
from src.workflows.infrastructure.repositories.sql_webhook_destination import (
    SQLWebhookDestinationRepository,
)
from src.workflows.infrastructure.repositories.sql_workflow import SQLWorkflowRepository
from src.workflows.infrastructure.repositories.sql_workflow_processing_job import (
    SQLWorkflowProcessingJobRepository,
)
from src.workflows.infrastructure.repositories.sql_workflow_event import SQLWorkflowEventRepository
from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    DispatchProcessingJobWebhookInput,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker

logger = get_logger(__name__)


class DispatchProcessingJobWebhookActivity:
    def __init__(
        self,
        session_maker: async_sessionmaker,
        dispatcher: WorkflowWebhookDispatcher | None = None,
    ) -> None:
        self._session_maker = session_maker
        self._dispatcher: WorkflowWebhookDispatcher = dispatcher or NoopWorkflowWebhookDispatcher()

    @activity.defn(name="dispatch_processing_job_webhook")
    async def dispatch_processing_job_webhook(self, payload: DispatchProcessingJobWebhookInput) -> None:
        data = DispatchProcessingJobWebhookInput.model_validate(payload)
        try:
            async with self._session_maker() as session:
                await DispatchProcessingJobWebhooks(
                    processing_job_id=data.processing_job_uuid,
                    workflow_id=data.workflow_id,
                    run_id=data.run_id,
                    final_status=data.final_status,
                    webhook_projection=data.webhook_projection,
                    workflow_repository=SQLWorkflowRepository(session=session),
                    processing_job_repository=SQLWorkflowProcessingJobRepository(session=session),
                    document_repository=SQLWorkflowDocumentRepository(session=session),
                    document_type_repository=SQLDocumentTypeRepository(session=session),
                    workflow_event_repository=SQLWorkflowEventRepository(session=session),
                    webhook_destination_repository=SQLWebhookDestinationRepository(session=session),
                    dispatcher=self._dispatcher,
                ).execute()
        except Exception as exc:  # fire-and-forget (§5.16)
            logger.warning(
                "dispatch_processing_job_webhook.failed",
                processing_job_uuid=str(data.processing_job_uuid),
                error=str(exc),
            )
