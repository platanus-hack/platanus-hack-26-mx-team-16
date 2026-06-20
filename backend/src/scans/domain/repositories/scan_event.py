"""``ScanEventRepository`` ABC (06-data-model §3.5, §4)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.scans.domain.contracts.events import ScanEvent


class ScanEventRepository(ABC):
    @abstractmethod
    async def append(self, event: ScanEvent) -> ScanEvent:
        """Append an event honoring the monotonic ``seq`` per scan. Reinserting an
        existing ``(scan_id, seq)`` violates the UNIQUE constraint (§4)."""
        raise NotImplementedError

    @abstractmethod
    async def next_seq(self, scan_id: UUID) -> int:
        """Return the next monotonic ``seq`` for ``scan_id`` (max + 1, or 0)."""
        raise NotImplementedError

    @abstractmethod
    async def replay(self, scan_id: UUID, *, after_seq: int | None = None) -> list[ScanEvent]:
        """Return events for ``scan_id`` ordered by ``seq`` (deterministic replay);
        optionally only those with ``seq > after_seq`` (live-view reconnect)."""
        raise NotImplementedError
