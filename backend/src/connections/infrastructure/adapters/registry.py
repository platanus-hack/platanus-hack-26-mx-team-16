"""Provider → adapter registry (F12).

Maps each :class:`ConnectionProvider` to its concrete Source / Destination
adapter instance. ``get_source_adapter`` / ``get_destination_adapter`` return an
instance or ``None`` when the provider does not support that direction.

``WEBHOOK`` maps to ``None`` in both directions: inbound webhooks are handled by
the ``POST /v1/ingest/{token}`` endpoint and outbound webhooks by the existing
HTTP destination dispatcher, so no adapter is needed here. ``HTTP`` is a lookup
Tool transport (F5 · A3), not a Source/Destination, so it also maps to ``None``.

``EMAIL`` / ``WHATSAPP`` are **not** polled sources: as of E6 (W5) they are
push channels handled by ``POST /v1/channels/{provider}/{token}`` and the
``infrastructure/channels`` adapter registry (``ChannelAdapter``), so they map
to ``None`` here too.
"""

from __future__ import annotations

from src.common.domain.enums.connections import ConnectionProvider
from src.connections.domain.adapters.base import DestinationAdapter, SourceAdapter
from src.connections.infrastructure.adapters.drive import (
    DriveDestinationAdapter,
    DriveSourceAdapter,
)
from src.connections.infrastructure.adapters.slack import SlackDestinationAdapter

# Inbound providers (Origins). WEBHOOK → ingest endpoint; EMAIL/WHATSAPP →
# push channels (POST /v1/channels/...) — all None here.
ADAPTER_SOURCES: dict[ConnectionProvider, SourceAdapter | None] = {
    ConnectionProvider.WEBHOOK: None,
    ConnectionProvider.DRIVE: DriveSourceAdapter(),
    ConnectionProvider.EMAIL: None,
    ConnectionProvider.WHATSAPP: None,
}

# Outbound providers (Destinations). WEBHOOK is handled by the HTTP dispatcher → None.
ADAPTER_DESTINATIONS: dict[ConnectionProvider, DestinationAdapter | None] = {
    ConnectionProvider.WEBHOOK: None,
    ConnectionProvider.SLACK: SlackDestinationAdapter(),
    ConnectionProvider.DRIVE: DriveDestinationAdapter(),
}


def get_source_adapter(provider: ConnectionProvider) -> SourceAdapter | None:
    """Return the Source adapter for ``provider`` or ``None`` if unsupported."""
    return ADAPTER_SOURCES.get(provider)


def get_destination_adapter(provider: ConnectionProvider) -> DestinationAdapter | None:
    """Return the Destination adapter for ``provider`` or ``None`` if unsupported."""
    return ADAPTER_DESTINATIONS.get(provider)
