from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.enums.source_deliveries import SourceDeliveryStatus
from src.connections.domain.models.source_delivery import SourceDelivery


class SourceDeliveryRepository(ABC):
    """Persistence for the inbound channel dedup ledger (E6 · §5.9)."""

    @abstractmethod
    async def insert_if_absent(self, delivery: SourceDelivery) -> tuple[SourceDelivery, bool]:
        """Delivery-first idempotent insert keyed by ``UNIQUE(source_id, idempotency_key)``.

        Returns ``(delivery, created)``: ``created=True`` when this call wrote
        the row, ``created=False`` (with the EXISTING row) when the key was
        already present. A duplicate is NOT an error — the caller short-circuits
        to a 200 idempotent response with no side effects.
        """
        raise NotImplementedError

    @abstractmethod
    async def mark_status(
        self,
        delivery_id: UUID,
        status: SourceDeliveryStatus,
        *,
        case_id: UUID | None = None,
        error: str | None = None,
    ) -> SourceDelivery | None:
        """Patch the lifecycle of a recorded delivery (processed/failed)."""
        raise NotImplementedError
