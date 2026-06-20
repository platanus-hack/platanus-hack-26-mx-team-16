"""Domain model for ``WorkflowEvent`` — the persisted outbound webhook event.

Append-only record of a workflow output event (spec ``standard-webhooks.md``
§4.1). One per finalized ``WorkflowDocument`` (EXTRACTED or ERROR). Carries the
immutable delivered ``payload`` snapshot plus the delivery state (audit + replay).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.webhooks import WebhookEventType, WorkflowEventDeliveryStatus


class WorkflowEvent(BaseModel):
    uuid: UUID
    tenant_id: UUID
    event_id: str  # public, ``evt_<uuid>`` → header ``Doxiq-Id``
    event_type: WebhookEventType
    workflow_id: UUID
    processing_job_id: UUID | None = None
    document_id: UUID | None = None
    destination_id: UUID | None = None  # webhook destination targeted (§4.3)
    idempotency_key: str  # = Temporal run_id (idempotency per run, §5.14)
    document_status: str  # WorkflowDocument.status: EXTRACTED | ERROR
    payload: dict  # immutable snapshot of the delivered body (§4.3)
    delivery_status: WorkflowEventDeliveryStatus = Field(default=WorkflowEventDeliveryStatus.PENDING)
    attempts: int = 0
    last_attempt_at: datetime | None = None
    delivered_at: datetime | None = None
    response_status: int | None = None
    last_error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")
