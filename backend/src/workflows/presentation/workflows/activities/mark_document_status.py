"""Activity that updates a single `workflow_documents` row during the
fan-out steps (`extract_fields`, `validate_extraction`).

Used for both the success path (write extraction + validation, mark
processing_status='completed') and the failure path (record the error,
mark processing_status='failed') so the workflow only carries one
helper.

After the row commits we fan out a `DashboardEvent` so the dashboard
tab can refetch the latest aggregates. The publish is fire-and-forget
— a Redis hiccup must never poison the Temporal activity.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio import activity

from src.common.application.logging import get_logger
from src.common.database.models.workflow_document import WorkflowDocumentORM
from src.common.domain.enums.processing_job_events import DocumentStatus
from src.common.domain.enums.workflows import WorkflowDocumentStatus
from src.common.infrastructure.event_publisher import EventPublisher
from src.dashboard.domain.events import DashboardEvent
from src.dashboard.domain.events.dashboard_event import (
    DashboardAffectedSection,
    DashboardEventType,
)
from src.workflows.domain.services.extraction_pages import collect_extraction_pages
from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    MarkDocumentInput,
)

logger = get_logger(__name__)


_DOCSTATUS_TO_LEGACY = {
    DocumentStatus.PENDING: WorkflowDocumentStatus.PROCESSING,
    DocumentStatus.EXTRACTING: WorkflowDocumentStatus.PROCESSING,
    DocumentStatus.VALIDATING: WorkflowDocumentStatus.PROCESSING,
    DocumentStatus.COMPLETED: WorkflowDocumentStatus.EXTRACTED,
    DocumentStatus.FAILED: WorkflowDocumentStatus.ERROR,
}


class MarkDocumentStatusActivity:
    def __init__(
        self,
        session_maker: async_sessionmaker,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._session_maker = session_maker
        self._event_publisher = event_publisher

    @activity.defn(name="mark_document_status")
    async def mark_document_status(self, payload: MarkDocumentInput) -> None:
        data = MarkDocumentInput.model_validate(payload)

        legacy = _DOCSTATUS_TO_LEGACY.get(data.status)
        values: dict = {
            "processing_status": data.status.value,
        }
        if legacy is not None:
            values["status"] = legacy.value
        if data.extraction is not None:
            values["extraction"] = data.extraction
        if data.mapped_extraction is not None:
            values["mapped_extraction"] = data.mapped_extraction
            pages = collect_extraction_pages(data.mapped_extraction)
            values["extraction_pages"] = pages or None
        if data.field_confidence is not None:
            values["field_confidence"] = data.field_confidence
        if data.needs_clarification is not None:
            values["needs_clarification"] = data.needs_clarification
        if data.validation is not None:
            values["validation"] = data.validation
        if data.extracted_text is not None:
            values["extracted_text"] = data.extracted_text
        if data.error is not None:
            values["error"] = data.error
            logger.warning(f"mark_document_status.error document_id={data.document_id} error={data.error}")

        async with self._session_maker() as session:
            # RETURNING fetches `tenant_id` so the dashboard fan-out doesn't
            # need a follow-up SELECT — the row is already locked from the
            # UPDATE and the tenant binding is invariant for the row's
            # lifetime, so this is safe + cheap.
            result = await session.execute(
                update(WorkflowDocumentORM)
                .where(WorkflowDocumentORM.uuid == data.document_id)
                .values(**values)
                .returning(WorkflowDocumentORM.tenant_id)
            )
            row = result.first()
            await session.commit()

        if row is not None:
            await self._publish_dashboard_event(
                tenant_id=row.tenant_id, status=data.status
            )

    async def _publish_dashboard_event(self, *, tenant_id: UUID, status: DocumentStatus) -> None:
        if self._event_publisher is None:
            return

        event_type, affects = _map_dashboard_event(status)
        try:
            event = DashboardEvent.build(
                type=event_type,
                tenant_id=tenant_id,
                affects=affects,
                payload={"status": status.value},
            )
            await self._event_publisher.publish(event)
        except Exception as exc:
            # The publisher itself logs & swallows — this catch is the
            # belt-and-braces guard so even an unexpected error path
            # (e.g. malformed UUID) never crashes the Temporal activity.
            logger.warning(
                f"mark_document_status.dashboard_publish_failed status={status.value} error={exc}"
            )


def _map_dashboard_event(
    status: DocumentStatus,
) -> tuple[DashboardEventType, list[DashboardAffectedSection]]:
    """Map an internal `DocumentStatus` to the dashboard event type + sections.

    Terminal statuses (COMPLETED/FAILED) affect both Overview and
    Processing tabs; in-flight sub-stage transitions only affect
    Processing — the Overview tab doesn't render anything that would
    change.
    """

    if status is DocumentStatus.COMPLETED:
        return "DOCUMENT_COMPLETED", ["overview", "processing"]
    if status is DocumentStatus.FAILED:
        return "DOCUMENT_FAILED", ["overview", "processing"]
    return "DOCUMENT_STATUS_CHANGED", ["processing"]
