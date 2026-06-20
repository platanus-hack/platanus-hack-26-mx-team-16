"""F12: provider adapter registry — WEBHOOK is None; others are NotImplemented stubs."""

import pytest
from expects import be_none, equal, expect

from src.common.domain.enums.connections import ConnectionProvider
from src.connections.infrastructure.adapters.registry import (
    get_destination_adapter,
    get_source_adapter,
)


def test_webhook_provider_has_no_adapter():
    # WEBHOOK is handled by the HTTP ingest endpoint / dispatcher, not an adapter.
    expect(get_source_adapter(ConnectionProvider.WEBHOOK)).to(be_none)
    expect(get_destination_adapter(ConnectionProvider.WEBHOOK)).to(be_none)


def test_drive_source_adapter_is_a_pending_stub():
    adapter = get_source_adapter(ConnectionProvider.DRIVE)

    expect(adapter is not None).to(equal(True))


async def test_pending_adapters_raise_not_implemented():
    source = get_source_adapter(ConnectionProvider.DRIVE)
    dest = get_destination_adapter(ConnectionProvider.SLACK)

    with pytest.raises(NotImplementedError):
        await source.poll(None)
    with pytest.raises(NotImplementedError):
        await dest.deliver(None, {})
