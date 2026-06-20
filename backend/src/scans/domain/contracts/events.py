"""FROZEN contract — ``events.py`` (06-data-model §6, backs ``scan_events`` §3.5).

The ``ScanEvent`` Pydantic shape congealed alongside ``finding.py`` in hour 0.
Corresponds 1:1 to the ``scan_events`` table. The ``seq`` is a per-scan monotonic
sequence and is the **single source of order** — it enables deterministic replay
of the live-view on reload (10-realtime-live-view). ``type`` is the discriminant.

Kept self-contained (Literal inlined, mirrors ``ScanEventType`` in
``enums/scans.py``) so any carril can import it without dragging infrastructure.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ScanEventTypeLiteral = Literal[
    "agent_status",
    "tool_start",
    "tool_end",
    "finding",
    "phase",
    "score",
    "done",
    "error",
]


class ScanEvent(BaseModel):
    """A single live-view event (spec §3.5).

    Ordering is guaranteed by ``(scan_id, seq)`` UNIQUE in the DB; ``seq`` is
    monotonic per scan. ``progress`` is set on ``phase``/``score`` events to drive
    the header bar; ``tool``/``severity`` are only present on the relevant types.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    scan_id: UUID
    seq: int  # monotonic per scan — single source of order
    ts: datetime
    type: ScanEventTypeLiteral  # discriminant
    agent: str | None = None
    tool: str | None = None
    severity: Literal["critical", "high", "medium", "low", "info"] | None = None
    message: str
    payload: dict = Field(default_factory=dict)
    progress: int | None = None  # 0..100 on phase/score events
