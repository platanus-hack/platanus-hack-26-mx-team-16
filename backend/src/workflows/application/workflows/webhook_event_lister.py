from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.workflow_event import WorkflowEvent
from src.workflows.domain.repositories.workflow_event import WorkflowEventRepository


@dataclass
class WorkflowEventsLister(UseCase):
    """List a workflow's webhook events for the delivery log (spec §10)."""

    workflow_id: UUID
    tenant_id: UUID
    workflow_event_repository: WorkflowEventRepository
    delivery_status: str | None = None
    limit: int = 50
    offset: int = 0

    async def execute(self) -> list[WorkflowEvent]:
        return await self.workflow_event_repository.list_by_workflow(
            workflow_id=self.workflow_id,
            tenant_id=self.tenant_id,
            delivery_status=self.delivery_status,
            limit=self.limit,
            offset=self.offset,
        )
