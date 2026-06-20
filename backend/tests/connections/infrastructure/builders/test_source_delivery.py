"""E6 W1: build_source_delivery ORM → domain roundtrip."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from expects import be_none, equal, expect

from src.common.database.models.source_delivery import SourceDeliveryORM
from src.common.domain.enums.source_deliveries import SourceDeliveryStatus
from src.connections.infrastructure.builders.source_delivery import build_source_delivery


def test_build_source_delivery__maps_all_fields():
    delivery_id = uuid4()
    source_id = uuid4()
    case_id = uuid4()
    created_at = datetime(2026, 6, 10, 9, 0, tzinfo=timezone.utc)
    orm = SourceDeliveryORM(
        uuid=delivery_id,
        source_id=source_id,
        idempotency_key="Message-ID:<abc@mail>",
        provider_message_id="<abc@mail>",
        status="processed",
        error=None,
        case_id=case_id,
        created_at=created_at,
    )

    delivery = build_source_delivery(orm)

    expect(delivery.uuid).to(equal(delivery_id))
    expect(delivery.source_id).to(equal(source_id))
    expect(delivery.idempotency_key).to(equal("Message-ID:<abc@mail>"))
    expect(delivery.provider_message_id).to(equal("<abc@mail>"))
    expect(delivery.status).to(equal(SourceDeliveryStatus.PROCESSED))
    expect(delivery.error).to(be_none)
    expect(delivery.case_id).to(equal(case_id))
    expect(delivery.created_at).to(equal(created_at))


def test_build_source_delivery__defaults_for_received_row():
    orm = SourceDeliveryORM(
        uuid=uuid4(),
        source_id=uuid4(),
        idempotency_key="wamid.HBgL",
        provider_message_id="wamid.HBgL",
        status="received",
        error=None,
        case_id=None,
        created_at=datetime.now(timezone.utc),
    )

    delivery = build_source_delivery(orm)

    expect(delivery.status).to(equal(SourceDeliveryStatus.RECEIVED))
    expect(delivery.case_id).to(be_none)
    expect(delivery.error).to(be_none)
