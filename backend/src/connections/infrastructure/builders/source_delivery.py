from src.common.database.models.source_delivery import SourceDeliveryORM
from src.common.domain.enums.source_deliveries import SourceDeliveryStatus
from src.connections.domain.models.source_delivery import SourceDelivery


def build_source_delivery(orm: SourceDeliveryORM) -> SourceDelivery:
    return SourceDelivery(
        uuid=orm.uuid,
        source_id=orm.source_id,
        idempotency_key=orm.idempotency_key,
        provider_message_id=orm.provider_message_id,
        status=SourceDeliveryStatus(orm.status),
        error=orm.error,
        case_id=orm.case_id,
        created_at=orm.created_at,
    )
