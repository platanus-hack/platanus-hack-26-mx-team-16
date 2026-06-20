"""DashboardEvent — tenant-scoped event used as an invalidation signal.

The dashboard does NOT receive its data over SSE; the REST endpoints
(`/v1/dashboard/overview`, `/v1/dashboard/processing`) carry the payload.
This event is a thin "something changed" signal that the frontend uses
to invalidate the TanStack Query cache and refetch only the affected
tab(s).

Channel naming follows the project convention `<scope>:<id>:<topic>:events`.
The channel is tenant-wide because the dashboard aggregates across
all workflows — a per-workflow channel would force the frontend to
multiplex multiple subscriptions for no benefit.

Ownership is enforced by the SSE endpoint (the authenticated user can
only subscribe to their own tenant's channel); there is no cross-tenant
risk from the channel name itself.
"""

import time
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import ConfigDict

from src.common.domain.events.base import Event

DashboardEventType = Literal[
    "DOCUMENT_CREATED",
    "DOCUMENT_STATUS_CHANGED",
    "DOCUMENT_FAILED",
    "DOCUMENT_COMPLETED",
]

DashboardAffectedSection = Literal["overview", "processing"]


def channel_for_dashboard(tenant_id: UUID) -> str:
    return f"tenant:{tenant_id.hex}:dashboard:events"


class DashboardEvent(Event):
    """Concrete event carried over the tenant dashboard channel.

    `affects` lets the frontend invalidate only the relevant tab — e.g.
    a sub-stage update (`processing_status` changing from OCR to
    EXTRACTION) only affects the Processing tab and should not force
    the Overview tab to refetch.
    """

    type: DashboardEventType
    tenant_id: UUID
    affects: list[DashboardAffectedSection]

    model_config = ConfigDict(extra="forbid")

    @property
    def channel(self) -> str:
        return channel_for_dashboard(self.tenant_id)

    @classmethod
    def build(
        cls,
        *,
        type: DashboardEventType,
        tenant_id: UUID,
        affects: list[DashboardAffectedSection],
        payload: dict | None = None,
        seq: int | None = None,
        ts: datetime | None = None,
    ) -> "DashboardEvent":
        """Canonical constructor that defaults `seq`/`ts` to "now".

        Mirrors `ProcessingJobEvent.build(...)` so every publish site uses
        the same conventions and we never end up with mismatched seq/ts
        encodings across the codebase.
        """

        return cls(
            seq=seq if seq is not None else int(time.time() * 1000),
            ts=ts if ts is not None else datetime.now(UTC),
            type=type,
            tenant_id=tenant_id,
            affects=affects,
            payload=payload or {},
        )
