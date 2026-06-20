"""SQLAlchemy implementation of WebhookDestinationRepository."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.webhook_destination import WebhookDestinationORM
from src.common.domain.enums.webhooks import WebhookEventType
from src.common.domain.models.webhook_destination import WebhookDestination
from src.common.infrastructure.helpers.database import atomic_transaction
from src.workflows.domain.repositories.webhook_destination import WebhookDestinationRepository
from src.workflows.infrastructure.builders.webhook_destination import build_webhook_destination


class SQLWebhookDestinationRepository(WebhookDestinationRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, destination: WebhookDestination) -> WebhookDestination:
        async with atomic_transaction(self.session):
            orm_instance = WebhookDestinationORM(
                uuid=destination.uuid,
                tenant_id=destination.tenant_id,
                workflow_id=destination.workflow_id,
                provider=destination.provider.value,
                account_id=destination.account_id,
                name=destination.name,
                url=destination.url,
                description=destination.description,
                enabled=destination.enabled,
                secret=destination.secret,
                subscribed_events=destination.subscribed_events,
                api_version=destination.api_version,
            )
            self.session.add(orm_instance)
            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_webhook_destination(orm_instance)

    async def update(self, destination: WebhookDestination) -> WebhookDestination:
        async with atomic_transaction(self.session):
            stmt = select(WebhookDestinationORM).where(
                WebhookDestinationORM.uuid == destination.uuid,
                WebhookDestinationORM.tenant_id == destination.tenant_id,
            )
            result = await self.session.execute(stmt)
            orm_instance = result.scalar_one()
            orm_instance.name = destination.name
            orm_instance.url = destination.url
            orm_instance.description = destination.description
            orm_instance.enabled = destination.enabled
            orm_instance.subscribed_events = destination.subscribed_events
            orm_instance.api_version = destination.api_version
            if destination.secret is not None:
                orm_instance.secret = destination.secret
            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_webhook_destination(orm_instance)

    async def find_by_id(self, destination_id: UUID, tenant_id: UUID) -> WebhookDestination | None:
        stmt = select(WebhookDestinationORM).where(
            WebhookDestinationORM.uuid == destination_id,
            WebhookDestinationORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        try:
            orm_instance = result.scalar_one()
        except NoResultFound:
            return None
        return build_webhook_destination(orm_instance)

    async def list_by_workflow(
        self, workflow_id: UUID, tenant_id: UUID
    ) -> list[WebhookDestination]:
        stmt = (
            select(WebhookDestinationORM)
            .where(
                WebhookDestinationORM.workflow_id == workflow_id,
                WebhookDestinationORM.tenant_id == tenant_id,
            )
            .order_by(WebhookDestinationORM.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [build_webhook_destination(orm) for orm in result.scalars()]

    async def list_enabled_for_event(
        self, workflow_id: UUID, tenant_id: UUID, event_type: WebhookEventType
    ) -> list[WebhookDestination]:
        stmt = select(WebhookDestinationORM).where(
            WebhookDestinationORM.workflow_id == workflow_id,
            WebhookDestinationORM.tenant_id == tenant_id,
            WebhookDestinationORM.enabled.is_(True),
        )
        result = await self.session.execute(stmt)
        return [
            build_webhook_destination(orm)
            for orm in result.scalars()
            if event_type.value in (orm.subscribed_events or [])
        ]

    async def delete(self, destination_id: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            stmt = delete(WebhookDestinationORM).where(
                WebhookDestinationORM.uuid == destination_id,
                WebhookDestinationORM.tenant_id == tenant_id,
            )
            await self.session.execute(stmt)
