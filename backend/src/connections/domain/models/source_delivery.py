"""Domain model for ``SourceDelivery`` — the inbound channel dedup ledger (E6 · §5.9).

Every native-channel message (email, WhatsApp) is recorded here **before** any
side effect (delivery-first). ``UNIQUE(source_id, idempotency_key)`` turns a
redelivered message into a no-op: ``SourceDeliveryRepository.insert_if_absent``
returns ``created=False`` for a key already seen. Lives in the ``connections``
module next to ``WorkflowSource`` (the source it dedups against).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.common.domain.enums.source_deliveries import SourceDeliveryStatus


class SourceDelivery(BaseModel):
    uuid: UUID
    source_id: UUID
    idempotency_key: str  # Message-ID (email) / wamid (WhatsApp) / fallback hash
    provider_message_id: str | None = None
    status: SourceDeliveryStatus = SourceDeliveryStatus.RECEIVED
    error: str | None = None
    case_id: UUID | None = None  # set once the delivery resolves to a case
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")
