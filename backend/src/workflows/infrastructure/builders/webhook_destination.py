from src.common.database.models.webhook_destination import WebhookDestinationORM
from src.common.domain.enums.connections import ConnectionProvider
from src.common.domain.models.webhook_destination import WebhookDestination


def build_webhook_destination(orm_instance: WebhookDestinationORM) -> WebhookDestination:
    """Map a ``WebhookDestinationORM`` row to the domain model."""
    return WebhookDestination(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        workflow_id=orm_instance.workflow_id,
        provider=ConnectionProvider(orm_instance.provider),
        account_id=orm_instance.account_id,
        name=orm_instance.name,
        url=orm_instance.url,
        description=orm_instance.description,
        enabled=orm_instance.enabled,
        secret=orm_instance.secret,
        subscribed_events=orm_instance.subscribed_events,
        api_version=orm_instance.api_version,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
