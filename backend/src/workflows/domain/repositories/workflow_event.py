from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.enums.webhooks import WebhookEventType
from src.common.domain.models.workflow_event import WorkflowEvent


class WorkflowEventRepository(ABC):
    """Persistence for append-only outbound webhook events (spec §4.1)."""

    @abstractmethod
    async def create(self, event: WorkflowEvent) -> WorkflowEvent:
        raise NotImplementedError

    @abstractmethod
    async def update(self, event: WorkflowEvent) -> WorkflowEvent:
        """Persist mutable delivery fields (status/attempts/timestamps/error)."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, event_uuid: UUID, tenant_id: UUID) -> WorkflowEvent | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_unique(
        self,
        document_id: UUID,
        event_type: WebhookEventType,
        idempotency_key: str,
    ) -> WorkflowEvent | None:
        """Idempotency lookup for the (document, type, run) unique key (§4.1)."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_unique_destination(
        self,
        document_id: UUID,
        event_type: WebhookEventType,
        idempotency_key: str,
        destination_id: UUID | None,
    ) -> WorkflowEvent | None:
        """Idempotency lookup keyed by (document, type, run, destination) (§4.3)."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_set(self, processing_job_id: UUID, tenant_id: UUID) -> list[WorkflowEvent]:
        raise NotImplementedError

    @abstractmethod
    async def list_by_destination(
        self,
        destination_id: UUID,
        tenant_id: UUID,
        delivery_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkflowEvent]:
        """Delivery log for one destination (§10), newest first, optional filter."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_workflow(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        delivery_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkflowEvent]:
        """Delivery log for the UI (§10), newest first, optional status filter."""
        raise NotImplementedError

    @abstractmethod
    async def list_for_retry(self, limit: int = 100) -> list[WorkflowEvent]:
        """Pending/failed events for the scheduled retry job (§4.8), cross-tenant."""
        raise NotImplementedError
