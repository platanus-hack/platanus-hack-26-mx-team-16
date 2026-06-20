"""E6 W1: SQLSourceDeliveryRepository — delivery-first idempotency + mark_status."""

from __future__ import annotations

from uuid import uuid4

import pytest
from expects import be_none, equal, expect

from src.common.domain.enums.source_deliveries import SourceDeliveryStatus
from src.connections.domain.models.source_delivery import SourceDelivery
from src.connections.infrastructure.repositories.sql_source_delivery import (
    SQLSourceDeliveryRepository,
)


@pytest.fixture
def delivery_repo(async_session):
    return SQLSourceDeliveryRepository(session=async_session)


def _delivery(source_id, key: str, provider_message_id: str | None = None) -> SourceDelivery:
    return SourceDelivery(
        uuid=uuid4(),
        source_id=source_id,
        idempotency_key=key,
        provider_message_id=provider_message_id or key,
    )


async def test_insert_if_absent__records_first_delivery(delivery_repo, source_orm):
    delivery = _delivery(source_orm.uuid, "Message-ID:<first@mail>")

    stored, created = await delivery_repo.insert_if_absent(delivery)

    expect(created).to(equal(True))
    expect(stored.uuid).to(equal(delivery.uuid))
    expect(stored.idempotency_key).to(equal("Message-ID:<first@mail>"))
    expect(stored.status).to(equal(SourceDeliveryStatus.RECEIVED))
    expect(stored.created_at is not None).to(equal(True))


async def test_insert_if_absent__second_same_key_is_idempotent(delivery_repo, source_orm):
    first = _delivery(source_orm.uuid, "wamid.HBgL")
    stored_first, created_first = await delivery_repo.insert_if_absent(first)

    # Redelivery: brand-new row uuid, SAME (source_id, idempotency_key).
    retry = _delivery(source_orm.uuid, "wamid.HBgL")
    stored_retry, created_retry = await delivery_repo.insert_if_absent(retry)

    expect(created_first).to(equal(True))
    expect(created_retry).to(equal(False))
    # The existing row is returned — NOT the retry's uuid.
    expect(stored_retry.uuid).to(equal(stored_first.uuid))


async def test_insert_if_absent__reclaims_failed_row_for_retry(delivery_repo, source_orm):
    # A delivery that committed RECEIVED, then FAILED (e.g. expired media URL),
    # must be retriable: a provider redelivery of the same idempotency_key
    # reclaims the FAILED row to RECEIVED and reports claimed=True so the message
    # is reprocessed instead of being lost as a duplicate.
    stored, created = await delivery_repo.insert_if_absent(
        _delivery(source_orm.uuid, "wamid.FAILED")
    )
    expect(created).to(equal(True))
    await delivery_repo.mark_status(
        stored.uuid, SourceDeliveryStatus.FAILED, error="media URL expired"
    )

    reclaimed, claimed = await delivery_repo.insert_if_absent(
        _delivery(source_orm.uuid, "wamid.FAILED")
    )

    # Reclaimed → claimed so the caller runs the pipeline again.
    expect(claimed).to(equal(True))
    # Same physical row, flipped back to RECEIVED (not the redelivery's uuid).
    expect(reclaimed.uuid).to(equal(stored.uuid))
    expect(reclaimed.status).to(equal(SourceDeliveryStatus.RECEIVED))


async def test_insert_if_absent__processed_row_stays_duplicate(delivery_repo, source_orm):
    # A completed PROCESSED delivery must NOT be reclaimed: a redelivery is a
    # genuine duplicate (claimed=False) so we never reprocess a finished message.
    stored, _ = await delivery_repo.insert_if_absent(_delivery(source_orm.uuid, "wamid.DONE"))
    await delivery_repo.mark_status(
        stored.uuid, SourceDeliveryStatus.PROCESSED, case_id=uuid4()
    )

    again, claimed = await delivery_repo.insert_if_absent(_delivery(source_orm.uuid, "wamid.DONE"))

    expect(claimed).to(equal(False))
    expect(again.uuid).to(equal(stored.uuid))
    expect(again.status).to(equal(SourceDeliveryStatus.PROCESSED))


async def test_insert_if_absent__received_row_stays_duplicate(delivery_repo, source_orm):
    # An in-flight RECEIVED delivery is also a duplicate (claimed=False): this
    # protects against double-processing a delivery still being handled.
    stored, _ = await delivery_repo.insert_if_absent(_delivery(source_orm.uuid, "wamid.INFLIGHT"))

    again, claimed = await delivery_repo.insert_if_absent(
        _delivery(source_orm.uuid, "wamid.INFLIGHT")
    )

    expect(claimed).to(equal(False))
    expect(again.uuid).to(equal(stored.uuid))
    expect(again.status).to(equal(SourceDeliveryStatus.RECEIVED))


async def test_insert_if_absent__same_key_different_source_both_created(
    delivery_repo, source_orm, async_session, tenant_orm, workflow_orm
):
    from src.common.database.models.workflow_source import WorkflowSourceORM

    other_source = WorkflowSourceORM(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        provider="WHATSAPP",
        route_token=f"src_{uuid4().hex[:12]}",
    )
    async_session.add(other_source)
    await async_session.flush()

    _, created_a = await delivery_repo.insert_if_absent(_delivery(source_orm.uuid, "dup-key"))
    _, created_b = await delivery_repo.insert_if_absent(_delivery(other_source.uuid, "dup-key"))

    # UNIQUE is (source_id, idempotency_key): same key on a different source is fine.
    expect(created_a).to(equal(True))
    expect(created_b).to(equal(True))


async def test_mark_status__patches_to_processed_with_case(delivery_repo, source_orm):
    stored, _ = await delivery_repo.insert_if_absent(_delivery(source_orm.uuid, "k-processed"))
    case_id = uuid4()

    updated = await delivery_repo.mark_status(
        stored.uuid, SourceDeliveryStatus.PROCESSED, case_id=case_id
    )

    expect(updated is not None).to(equal(True))
    expect(updated.status).to(equal(SourceDeliveryStatus.PROCESSED))
    expect(updated.case_id).to(equal(case_id))
    expect(updated.error).to(be_none)


async def test_mark_status__patches_to_failed_with_error(delivery_repo, source_orm):
    stored, _ = await delivery_repo.insert_if_absent(_delivery(source_orm.uuid, "k-failed"))

    updated = await delivery_repo.mark_status(
        stored.uuid, SourceDeliveryStatus.FAILED, error="media URL expired"
    )

    expect(updated.status).to(equal(SourceDeliveryStatus.FAILED))
    expect(updated.error).to(equal("media URL expired"))


async def test_mark_status__unknown_delivery_returns_none(delivery_repo):
    result = await delivery_repo.mark_status(uuid4(), SourceDeliveryStatus.PROCESSED)

    expect(result).to(be_none)
