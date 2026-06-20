"""Use cases for per-workflow webhook destinations (spec connections §4.3).

Each workflow can register many webhook destinations; deliveries are recorded as
``WorkflowEvent`` rows tagged with the destination id (delivery log + charts).
"""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from src.common.application.helpers.webhooks.signing import generate_webhook_secret
from src.common.domain.exceptions.processing import WebhookDestinationNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.webhook_destination import WebhookDestination
from src.common.domain.models.workflow_event import WorkflowEvent
from src.workflows.domain.repositories.webhook_destination import WebhookDestinationRepository
from src.workflows.domain.repositories.workflow_event import WorkflowEventRepository

DEFAULT_EVENTS: tuple[str, ...] = ("document.extracted", "document.failed")


@dataclass
class CreateWebhookDestination(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    name: str
    url: str
    repo: WebhookDestinationRepository
    description: str | None = None
    enabled: bool = True
    subscribed_events: list[str] = field(default_factory=lambda: list(DEFAULT_EVENTS))
    secret: str | None = None
    api_version: str | None = None

    async def execute(self) -> WebhookDestination:
        destination = WebhookDestination(
            uuid=uuid4(),
            tenant_id=self.tenant_id,
            workflow_id=self.workflow_id,
            name=self.name,
            url=self.url,
            description=self.description,
            enabled=self.enabled,
            # Auto-generate a Svix-style signing secret when none was supplied.
            secret=self.secret or generate_webhook_secret(),
            subscribed_events=self.subscribed_events or list(DEFAULT_EVENTS),
            api_version=self.api_version,
        )
        return await self.repo.create(destination)


@dataclass
class ListWebhookDestinations(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    repo: WebhookDestinationRepository

    async def execute(self) -> list[WebhookDestination]:
        return await self.repo.list_by_workflow(self.workflow_id, self.tenant_id)


@dataclass
class GetWebhookDestination(UseCase):
    workflow_id: UUID
    destination_id: UUID
    tenant_id: UUID
    repo: WebhookDestinationRepository

    async def execute(self) -> WebhookDestination:
        destination = await self.repo.find_by_id(self.destination_id, self.tenant_id)
        if destination is None or destination.workflow_id != self.workflow_id:
            raise WebhookDestinationNotFoundError(str(self.destination_id))
        return destination


@dataclass
class UpdateWebhookDestination(UseCase):
    workflow_id: UUID
    destination_id: UUID
    tenant_id: UUID
    repo: WebhookDestinationRepository
    name: str | None = None
    url: str | None = None
    description: str | None = None
    enabled: bool | None = None
    subscribed_events: list[str] | None = None
    secret: str | None = None
    api_version: str | None = None

    async def execute(self) -> WebhookDestination:
        destination = await self.repo.find_by_id(self.destination_id, self.tenant_id)
        if destination is None or destination.workflow_id != self.workflow_id:
            raise WebhookDestinationNotFoundError(str(self.destination_id))

        if self.name is not None:
            destination.name = self.name
        if self.url is not None:
            destination.url = self.url
        if self.description is not None:
            destination.description = self.description
        if self.enabled is not None:
            destination.enabled = self.enabled
        if self.subscribed_events is not None:
            destination.subscribed_events = self.subscribed_events
        if self.api_version is not None:
            destination.api_version = self.api_version
        if self.secret is not None:
            destination.secret = self.secret
        return await self.repo.update(destination)


@dataclass
class DeleteWebhookDestination(UseCase):
    workflow_id: UUID
    destination_id: UUID
    tenant_id: UUID
    repo: WebhookDestinationRepository

    async def execute(self) -> None:
        destination = await self.repo.find_by_id(self.destination_id, self.tenant_id)
        if destination is None or destination.workflow_id != self.workflow_id:
            raise WebhookDestinationNotFoundError(str(self.destination_id))
        await self.repo.delete(self.destination_id, self.tenant_id)


@dataclass
class RegenerateWebhookDestinationSecret(UseCase):
    workflow_id: UUID
    destination_id: UUID
    tenant_id: UUID
    repo: WebhookDestinationRepository

    async def execute(self) -> WebhookDestination:
        destination = await self.repo.find_by_id(self.destination_id, self.tenant_id)
        if destination is None or destination.workflow_id != self.workflow_id:
            raise WebhookDestinationNotFoundError(str(self.destination_id))
        destination.secret = generate_webhook_secret()
        return await self.repo.update(destination)


@dataclass
class ListWebhookDestinationEvents(UseCase):
    """Delivery log for a single destination (spec §10), newest first."""

    destination_id: UUID
    tenant_id: UUID
    workflow_event_repository: WorkflowEventRepository
    delivery_status: str | None = None
    limit: int = 50
    offset: int = 0

    async def execute(self) -> list[WorkflowEvent]:
        return await self.workflow_event_repository.list_by_destination(
            destination_id=self.destination_id,
            tenant_id=self.tenant_id,
            delivery_status=self.delivery_status,
            limit=self.limit,
            offset=self.offset,
        )
