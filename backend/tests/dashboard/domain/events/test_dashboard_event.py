from datetime import UTC, datetime
from uuid import UUID, uuid4

from expects import be_a, equal, expect

from src.common.domain.events.base import Event
from src.dashboard.domain.events.dashboard_event import (
    DashboardEvent,
    channel_for_dashboard,
)


def test_channel_for_dashboard__embeds_tenant_hex():
    tenant_id = UUID("0b2b354b-8cef-4dca-8bf8-c7959de572a0")

    result = channel_for_dashboard(tenant_id)

    expect(result).to(equal("tenant:0b2b354b8cef4dca8bf8c7959de572a0:dashboard:events"))


def test_channel_for_dashboard__is_stable_for_same_uuid():
    tenant_id = uuid4()

    first = channel_for_dashboard(tenant_id)
    second = channel_for_dashboard(tenant_id)

    expect(first).to(equal(second))


def test_channel_for_dashboard__differs_across_tenants():
    a = channel_for_dashboard(uuid4())
    b = channel_for_dashboard(uuid4())

    expect(a).not_to(equal(b))


def test_dashboard_event_is_an_event_subclass():
    expect(issubclass(DashboardEvent, Event)).to(equal(True))


def test_build__defaults_seq_to_milliseconds_timestamp():
    tenant_id = uuid4()

    event = DashboardEvent.build(
        type="DOCUMENT_CREATED",
        tenant_id=tenant_id,
        affects=["overview", "processing"],
    )

    # ms-since-epoch is a 13-digit number for any current/future date.
    expect(event.seq).to(be_a(int))
    expect(len(str(event.seq))).to(equal(13))


def test_build__defaults_ts_to_now_utc():
    before = datetime.now(UTC)

    event = DashboardEvent.build(
        type="DOCUMENT_CREATED",
        tenant_id=uuid4(),
        affects=["overview"],
    )

    after = datetime.now(UTC)
    expect(event.ts).to(be_a(datetime))
    expect(event.ts.tzinfo).to(equal(UTC))
    expect(before <= event.ts <= after).to(equal(True))


def test_build__accepts_explicit_seq_and_ts():
    fixed_ts = datetime(2026, 1, 1, tzinfo=UTC)

    event = DashboardEvent.build(
        type="DOCUMENT_COMPLETED",
        tenant_id=uuid4(),
        affects=["overview", "processing"],
        seq=42,
        ts=fixed_ts,
    )

    expect(event.seq).to(equal(42))
    expect(event.ts).to(equal(fixed_ts))


def test_build__default_payload_is_empty_dict():
    event = DashboardEvent.build(
        type="DOCUMENT_FAILED",
        tenant_id=uuid4(),
        affects=["processing"],
    )

    expect(event.payload).to(equal({}))


def test_build__preserves_provided_payload():
    payload = {"documentId": "doc-1", "fromStatus": "PROCESSING", "toStatus": "EXTRACTED"}

    event = DashboardEvent.build(
        type="DOCUMENT_STATUS_CHANGED",
        tenant_id=uuid4(),
        affects=["processing"],
        payload=payload,
    )

    expect(event.payload).to(equal(payload))


def test_channel_property__matches_channel_helper():
    tenant_id = uuid4()
    event = DashboardEvent.build(
        type="DOCUMENT_CREATED",
        tenant_id=tenant_id,
        affects=["overview"],
    )

    expect(event.channel).to(equal(channel_for_dashboard(tenant_id)))


def test_build__processing_only_affects_processing_section():
    event = DashboardEvent.build(
        type="DOCUMENT_STATUS_CHANGED",
        tenant_id=uuid4(),
        affects=["processing"],
    )

    expect(event.affects).to(equal(["processing"]))


def test_build__document_created_affects_both_sections():
    event = DashboardEvent.build(
        type="DOCUMENT_CREATED",
        tenant_id=uuid4(),
        affects=["overview", "processing"],
    )

    expect(event.affects).to(equal(["overview", "processing"]))
