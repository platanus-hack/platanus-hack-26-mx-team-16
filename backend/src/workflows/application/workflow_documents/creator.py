"""Create a single WorkflowDocument row (SINGLE source)."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.common.domain.enums.workflows import (
    WorkflowDocumentSource,
    WorkflowDocumentStatus,
)
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.infrastructure.event_publisher import EventPublisher
from src.dashboard.domain.events import DashboardEvent
from src.workflows.domain.repositories.workflow_document import (
    WorkflowDocumentRepository,
)


@dataclass
class WorkflowDocumentCreator(UseCase):
    tenant_id: UUID
    workflow_id: UUID
    file_id: UUID | None
    file_name: str | None
    document_type_id: UUID | None
    document_repository: WorkflowDocumentRepository
    case_id: UUID | None = None
    # Optional to stay backward-compatible with internal callers that don't
    # care about the dashboard signal (e.g. tests, scripts). Endpoints
    # injecting the dependency get the fan-out for free.
    event_publisher: EventPublisher | None = None

    async def execute(self) -> WorkflowDocument:
        document = WorkflowDocument(
            uuid=uuid4(),
            tenant_id=self.tenant_id,
            workflow_id=self.workflow_id,
            case_id=self.case_id,
            document_type_id=self.document_type_id,
            file_id=self.file_id,
            file_name=self.file_name,
            status=WorkflowDocumentStatus.UPLOADED,
            source=WorkflowDocumentSource.SINGLE,
        )
        persisted = await self.document_repository.create(document)
        await self._publish_dashboard_event(persisted)
        return persisted

    async def _publish_dashboard_event(self, document: WorkflowDocument) -> None:
        """Signal the dashboard to refresh — fire-and-forget after commit.

        The `RedisEventPublisher` swallows and logs its own failures, so
        a Redis hiccup never poisons this use case. When no publisher is
        wired in (unit tests, scripts) we just skip.
        """

        if self.event_publisher is None:
            return
        event = DashboardEvent.build(
            type="DOCUMENT_CREATED",
            tenant_id=self.tenant_id,
            affects=["overview", "processing"],
            payload={"documentId": str(document.uuid)},
        )
        await self.event_publisher.publish(event)
