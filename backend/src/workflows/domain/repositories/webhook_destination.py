from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.enums.webhooks import WebhookEventType
from src.common.domain.models.webhook_destination import WebhookDestination


class WebhookDestinationRepository(ABC):
    """Persistence for per-workflow webhook destinations (spec §4.3)."""

    @abstractmethod
    async def create(self, destination: WebhookDestination) -> WebhookDestination:
        raise NotImplementedError

    @abstractmethod
    async def update(self, destination: WebhookDestination) -> WebhookDestination:
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, destination_id: UUID, tenant_id: UUID) -> WebhookDestination | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_workflow(
        self, workflow_id: UUID, tenant_id: UUID
    ) -> list[WebhookDestination]:
        """All destinations for the workflow, newest first."""
        raise NotImplementedError

    @abstractmethod
    async def list_enabled_for_event(
        self, workflow_id: UUID, tenant_id: UUID, event_type: WebhookEventType
    ) -> list[WebhookDestination]:
        """Enabled destinations of the workflow subscribed to ``event_type`` (§4.6)."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, destination_id: UUID, tenant_id: UUID) -> None:
        raise NotImplementedError
