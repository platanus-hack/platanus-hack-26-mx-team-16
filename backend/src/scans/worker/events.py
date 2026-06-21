"""``ScanEventEmitter`` — the worker-side publisher for live-view events (10 §3).

The emitter is the **only** writer of ``scan_events`` during a run, and it
enforces the load-bearing invariant of the whole live view:

    1) Postgres FIRST  (``repo.append`` — the truth + the replay source)
    2) Redis  SECOND   (``redis.publish`` — the at-most-once tail)

If the publish fails, the event still sits in ``scan_events`` and a (re)connecting
client recovers it via replay. The reverse order is forbidden: an event published
but not persisted would be invisible to replay, defeating replay-then-tail.

``seq`` is monotonic **per scan** and is the single source of order. A single
emitter instance is closed over the whole run and shared by every carril (worker,
OWASP subagent, agentic subagent), so the ``seq`` it hands out stays globally
monotonic for the scan. The ``UNIQUE (scan_id, seq)`` constraint (06) is the
safety net: a double-emit of the same ``seq`` raises in ``append`` (a loud bug,
never silent corruption).

05/03/07 instantiate one emitter per scan and call ``emit(...)`` (or the typed
sugars) from inside the flow / tool wrappers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from src.common.application.logging import get_logger
from src.scans.domain.contracts.events import ScanEvent, ScanEventTypeLiteral
from src.scans.domain.repositories.scan_event import ScanEventRepository
from src.scans.infrastructure.sse.channels import scan_events_channel

logger = get_logger(__name__)

#: Terminal event types — emitting one of these closes the live stream (10 §4.2).
TERMINAL_EVENT_TYPES: frozenset[str] = frozenset({"done", "error"})


@dataclass
class ScanEventEmitter:
    """Per-scan event emitter. PG-write-before-Redis-publish; monotonic ``seq``.

    Args:
        scan_id: the scan this emitter belongs to.
        repo: ``ScanEventRepository`` (06) — the authoritative, replayable store.
        redis: the worker's shared Redis client (``ctx["redis"]``) — tail only.
        seq: last assigned ``seq`` (defaults to 0; first ``emit`` produces 1).
    """

    scan_id: UUID
    repo: ScanEventRepository
    redis: Redis
    seq: int = field(default=0)

    async def publish(self, scan_id: UUID, event: ScanEvent) -> None:
        """Durably append ``event`` to Postgres, THEN publish it to Redis.

        This is the clean low-level API for 05/03/07 producers that already
        built a fully-formed :class:`ScanEvent` (with its own ``seq``). The PG→Redis
        order is the invariant; do not publish without appending first.
        """
        await self.repo.append(event)  # 1) Postgres FIRST (truth + replay)
        await self.redis.publish(  # 2) Redis SECOND (tail)
            scan_events_channel(scan_id),
            event.model_dump_json(),
        )
        logger.debug(
            f"scan_event_emitter.published channel={scan_events_channel(scan_id)} "
            f"seq={event.seq} type={event.type}"
        )

    async def emit(
        self,
        type_: ScanEventTypeLiteral,
        *,
        message: str,
        agent: str | None = None,
        tool: str | None = None,
        severity: str | None = None,
        payload: dict[str, Any] | None = None,
        progress: int | None = None,
    ) -> ScanEvent:
        """Assign the next ``seq``, build the :class:`ScanEvent`, and publish it.

        The convenience entry point for the flow: it owns the monotonic ``seq``
        so callers never have to. Returns the persisted event.
        """
        self.seq += 1
        event = ScanEvent(
            scan_id=self.scan_id,
            seq=self.seq,
            ts=datetime.now(UTC),
            type=type_,
            agent=agent,
            tool=tool,
            severity=severity,
            message=message,
            payload=payload or {},
            progress=progress,
        )
        await self.publish(self.scan_id, event)
        return event

    # -- typed sugars (mirror the discriminant; thin wrappers over emit) --------

    async def agent_status(self, message: str, *, agent: str, **kw: Any) -> ScanEvent:
        return await self.emit("agent_status", message=message, agent=agent, **kw)

    async def tool_start(self, message: str, *, tool: str, **kw: Any) -> ScanEvent:
        return await self.emit("tool_start", message=message, tool=tool, **kw)

    async def tool_end(self, message: str, *, tool: str, **kw: Any) -> ScanEvent:
        return await self.emit("tool_end", message=message, tool=tool, **kw)

    async def finding(self, message: str, *, severity: str, **kw: Any) -> ScanEvent:
        return await self.emit("finding", message=message, severity=severity, **kw)

    async def phase(self, message: str, *, progress: int | None = None, **kw: Any) -> ScanEvent:
        return await self.emit("phase", message=message, progress=progress, **kw)

    async def score(self, message: str, *, payload: dict[str, Any], **kw: Any) -> ScanEvent:
        return await self.emit("score", message=message, payload=payload, **kw)

    async def done(self, message: str, *, outcome: str = "success", **kw: Any) -> ScanEvent:
        """Terminal success/cancel event. Cancellation is ``done{outcome:cancelled}``."""
        payload = {**kw.pop("payload", {}), "outcome": outcome}
        return await self.emit("done", message=message, payload=payload, **kw)

    async def error(self, message: str, **kw: Any) -> ScanEvent:
        """Terminal error event."""
        return await self.emit("error", message=message, **kw)
