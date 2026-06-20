"""Provider adapter contracts (F12).

Defines the structural ``Protocol`` interfaces a concrete provider adapter must
satisfy to act as an ingest Source or a delivery Destination. Implementations
live under ``src.connections.infrastructure.adapters`` and are resolved through
the registry by :class:`ConnectionProvider`.
"""

from src.connections.domain.adapters.base import DestinationAdapter, SourceAdapter

__all__ = ["DestinationAdapter", "SourceAdapter"]
