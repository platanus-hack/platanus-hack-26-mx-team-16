"""Single source of truth for the scan live-view Redis channel name (10 §3.1).

Both the worker emitter (``ScanEventEmitter.publish``) and the SSE endpoint
(``stream_scan``) import this so the publish channel and the subscribe channel
can never drift (the classic "publish to ``scan:{id}`` but subscribe to
``scan:{id}:events``" bug).
"""

from __future__ import annotations


def scan_events_channel(scan_id: object) -> str:
    """Redis pub/sub channel that carries live ``ScanEvent``s for one scan."""
    return f"scan:{scan_id}:events"
