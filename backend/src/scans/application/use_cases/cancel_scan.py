"""``CancelScan`` — ``POST /scans/{id}/cancel`` (12-api §"Cancelación").

Kills a hung scan (critical when hexstrike/garak stall mid-demo). Effects:

- Sets ``scans.status='cancelled'`` (a first-class scan status, NOT a
  ``scan_events.type``).
- Appends a **terminal** ``done`` event with ``payload={'outcome': 'cancelled'}``
  so the live-view (10) closes the stream cleanly. ``cancelled`` is a scan status,
  never an event type — the ``done`` event carries the outcome.
- Raises a Redis cancel flag the worker checks **between tools** (best-effort; it
  does not abort a tool mid-run, only prevents launching the next one). The flag
  key shape is shared with 04/05; failures to set it never fail the request.

Ownership (404 for non-owner) is enforced by ``require_scan_owner`` upstream;
this use case receives the already-authorized scan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from redis.asyncio import Redis

from src.common.domain.enums.scans import ScanStatus
from src.common.domain.interfaces.use_case import UseCase
from src.scans.domain.contracts.events import ScanEvent
from src.scans.domain.models.scan import Scan
from src.scans.domain.repositories.scan import ScanRepository
from src.scans.domain.repositories.scan_event import ScanEventRepository


def scan_cancel_flag_key(scan_id: object) -> str:
    """Redis key the worker polls between tools (shared with 04/05)."""
    return f"scan:{scan_id}:cancel"


@dataclass
class CancelScan(UseCase):
    scan: Scan
    scan_repository: ScanRepository
    scan_event_repository: ScanEventRepository
    redis_client: Redis | None = None

    async def execute(self, *args, **kwargs) -> Scan:
        await self.scan_repository.update_progress(
            self.scan.uuid, status=str(ScanStatus.CANCELLED)
        )

        # Best-effort terminal event so the SSE stream (10) ends with done/cancelled.
        try:
            seq = await self.scan_event_repository.next_seq(self.scan.uuid)
            await self.scan_event_repository.append(
                ScanEvent(
                    scan_id=self.scan.uuid,
                    seq=seq,
                    ts=datetime.now(UTC),
                    type="done",
                    message="Scan cancelled by user.",
                    payload={"outcome": "cancelled"},
                    progress=self.scan.progress,
                )
            )
        except Exception:
            # Event bookkeeping must never block the cancel itself.
            pass

        # Best-effort cancel flag the worker checks between tools.
        if self.redis_client is not None:
            try:
                await self.redis_client.set(
                    scan_cancel_flag_key(self.scan.uuid), "1", ex=3600
                )
            except Exception:
                pass

        cancelled = self.scan.model_copy(update={"status": str(ScanStatus.CANCELLED)})
        return cancelled
