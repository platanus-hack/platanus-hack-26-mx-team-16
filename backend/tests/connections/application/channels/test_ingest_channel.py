"""E6 · W5: IngestChannelMessage — case_strategy mapping + delivery-first dedup."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.domain.enums.connections import ConnectionProvider
from src.common.domain.enums.source_deliveries import SourceDeliveryStatus
from src.connections.application.channels.ingest_channel import (
    IngestChannelMessage,
    case_name_for,
)
from src.connections.domain.models.channel_message import ChannelMessage
from src.connections.domain.models.source_delivery import SourceDelivery
from src.connections.domain.models.workflow_source import WorkflowSource


def _message(**overrides) -> ChannelMessage:
    base = dict(
        provider="whatsapp",
        provider_message_id="wamid.AAA",
        sender="5215550001",
        recipient="PN1",
        received_at=datetime.now(UTC),
        text="hi",
        attachments=[],
        thread_ref="wamid.PARENT",
    )
    base.update(overrides)
    return ChannelMessage(**base)


def _source(config=None) -> WorkflowSource:
    return WorkflowSource(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        provider=ConnectionProvider.WHATSAPP,
        route_token="src_abc",
        config=config or {},
    )


# ── case_name_for (pure) ─────────────────────────────────────────────────────
def test_case_name_for__per_message_is_message_id():
    msg = _message()
    expect(case_name_for(msg, "per_message")).to(equal("wamid.AAA"))
    # default strategy is per_message
    expect(case_name_for(msg, "unknown")).to(equal("wamid.AAA"))


def test_case_name_for__per_sender_is_sender():
    expect(case_name_for(_message(), "per_sender")).to(equal("5215550001"))


def test_case_name_for__per_thread_falls_back_to_message_id():
    expect(case_name_for(_message(), "per_thread")).to(equal("wamid.PARENT"))
    expect(case_name_for(_message(thread_ref=None), "per_thread")).to(equal("wamid.AAA"))


# ── delivery-first dedup ─────────────────────────────────────────────────────
class _DeliveryRepo:
    """Models UNIQUE(source_id, idempotency_key) in memory."""

    def __init__(self):
        self.rows: dict[tuple, SourceDelivery] = {}
        self.marked: list[tuple] = []

    async def insert_if_absent(self, delivery: SourceDelivery):
        key = (delivery.source_id, delivery.idempotency_key)
        if key in self.rows:
            return self.rows[key], False
        self.rows[key] = delivery
        return delivery, True

    async def mark_status(self, delivery_id, status, *, case_id=None, error=None):
        self.marked.append((delivery_id, status, case_id, error))
        return None


class _ExplodingClient:
    async def start_workflow(self, *a, **k):  # pragma: no cover - must never run
        raise AssertionError("duplicate must not dispatch a workflow")


async def test_dedup__second_same_key_is_idempotent_with_no_side_effects():
    repo = _DeliveryRepo()
    source = _source()
    message = _message(provider_message_id="wamid.DUP")

    def make():
        return IngestChannelMessage(
            source=source,
            message=message,
            adapter=object(),
            session=object(),
            temporal_client=_ExplodingClient(),
            source_delivery_repository=repo,
        )

    # First insert wins (records RECEIVED); we stop it before heavy work by
    # asserting only on the SECOND call's idempotency here.
    first, created_first = await repo.insert_if_absent(
        SourceDelivery(uuid=uuid4(), source_id=source.uuid, idempotency_key="wamid.DUP")
    )
    expect(created_first).to(equal(True))

    result = await make().execute()

    expect(result.duplicate).to(equal(True))
    expect(result.delivery_id).to(equal(first.uuid))
    # No FAILED/PROCESSED mark, no workflow dispatched.
    expect(repo.marked).to(equal([]))


async def test_dedup__failure_marks_delivery_failed_and_reraises(monkeypatch):
    repo = _DeliveryRepo()
    source = _source()

    use_case = IngestChannelMessage(
        source=source,
        message=_message(provider_message_id="wamid.NEW"),
        adapter=object(),
        session=object(),
        temporal_client=object(),
        source_delivery_repository=repo,
    )

    async def boom(_delivery_id):
        raise RuntimeError("processing blew up")

    monkeypatch.setattr(use_case, "_process", boom)

    with pytest.raises(RuntimeError):
        await use_case.execute()

    expect(len(repo.marked)).to(equal(1))
    _id, status, _case, error = repo.marked[0]
    expect(status).to(equal(SourceDeliveryStatus.FAILED))
    expect("processing blew up" in error).to(equal(True))
