"""SQLAlchemy implementation of SourceDeliveryRepository (E6 · §5.9)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.source_delivery import SourceDeliveryORM
from src.common.domain.enums.source_deliveries import SourceDeliveryStatus
from src.common.infrastructure.helpers.database import atomic_transaction
from src.connections.domain.models.source_delivery import SourceDelivery
from src.connections.domain.repositories.source_delivery import SourceDeliveryRepository
from src.connections.infrastructure.builders.source_delivery import build_source_delivery


class SQLSourceDeliveryRepository(SourceDeliveryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert_if_absent(self, delivery: SourceDelivery) -> tuple[SourceDelivery, bool]:
        # Delivery-first: rely on UNIQUE(source_id, idempotency_key) to make a
        # redelivered message idempotent. The second element is "claimed" — True
        # when the caller OWNS this delivery and must process it, False when it is
        # a genuine duplicate to skip with no side effects.
        #
        # ON CONFLICT DO UPDATE reclaims a row left in FAILED by a previous run
        # (e.g. an expired WhatsApp media URL): it flips status back to RECEIVED
        # so a provider redelivery retries instead of being lost. The WHERE guard
        # only matches FAILED, so an in-flight RECEIVED row (protect against
        # double-processing) or a completed PROCESSED row (protect against
        # reprocessing) updates nothing and returns no row → duplicate.
        #
        # A new INSERT and a reclaimed UPDATE both RETURN the row → claimed=True
        # (the caller processes either way). Only a non-FAILED conflict returns
        # no row → claimed=False (skip).
        async with atomic_transaction(self.session):
            stmt = (
                pg_insert(SourceDeliveryORM)
                .values(
                    uuid=delivery.uuid,
                    source_id=delivery.source_id,
                    idempotency_key=delivery.idempotency_key,
                    provider_message_id=delivery.provider_message_id,
                    status=delivery.status.value,
                    error=delivery.error,
                    case_id=delivery.case_id,
                )
                .on_conflict_do_update(
                    constraint="uq_source_deliveries_source_key",
                    set_={"status": SourceDeliveryStatus.RECEIVED.value},
                    where=SourceDeliveryORM.status == SourceDeliveryStatus.FAILED.value,
                )
                .returning(SourceDeliveryORM.uuid)
            )
            claimed_uuid = (await self.session.execute(stmt)).scalar_one_or_none()

        if claimed_uuid is not None:
            orm = (
                await self.session.execute(
                    select(SourceDeliveryORM).where(SourceDeliveryORM.uuid == claimed_uuid)
                )
            ).scalar_one()
            return build_source_delivery(orm), True

        existing = (
            await self.session.execute(
                select(SourceDeliveryORM).where(
                    SourceDeliveryORM.source_id == delivery.source_id,
                    SourceDeliveryORM.idempotency_key == delivery.idempotency_key,
                )
            )
        ).scalar_one()
        return build_source_delivery(existing), False

    async def mark_status(
        self,
        delivery_id: UUID,
        status: SourceDeliveryStatus,
        *,
        case_id: UUID | None = None,
        error: str | None = None,
    ) -> SourceDelivery | None:
        async with atomic_transaction(self.session):
            orm = (
                await self.session.execute(
                    select(SourceDeliveryORM).where(SourceDeliveryORM.uuid == delivery_id)
                )
            ).scalar_one_or_none()
            if orm is None:
                return None
            orm.status = status.value
            if case_id is not None:
                orm.case_id = case_id
            if error is not None:
                orm.error = error
            await self.session.flush()
            await self.session.refresh(orm)
        return build_source_delivery(orm)
