"""Google Drive provider adapters (F12 scaffold).

Drive can act as both an ingest Source (inbound documents from a watched folder)
and a delivery Destination (push results to a folder). Both flows depend on the
external OAuth/credential flow, which is pending.
"""

from __future__ import annotations

from src.common.domain.models.webhook_destination import WebhookDestination
from src.connections.domain.models.workflow_source import WorkflowSource


class DriveSourceAdapter:
    """Polls a watched Drive folder for new documents (F12 · pending)."""

    async def poll(self, source: WorkflowSource) -> list[dict]:
        raise NotImplementedError(
            "F12: OAuth/credential flow pending — external. "
            "DriveSourceAdapter.poll requires a connected Drive account."
        )


class DriveDestinationAdapter:
    """Delivers result payloads into a Drive folder (F12 · pending)."""

    async def deliver(self, destination: WebhookDestination, payload: dict) -> dict:
        raise NotImplementedError(
            "F12: OAuth/credential flow pending — external. "
            "DriveDestinationAdapter.deliver requires a connected Drive account."
        )
