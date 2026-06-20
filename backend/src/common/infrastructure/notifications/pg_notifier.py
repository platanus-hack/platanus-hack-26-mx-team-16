"""Postgres LISTEN/NOTIFY fan-out for pushing domain events to SSE subscribers.

Flow:
1. A background asyncpg connection holds `LISTEN` on a channel for the app's lifetime.
2. Writers (activities, endpoints) emit events via `NOTIFY <channel>, '<json>'`.
3. Subscribers call `subscribe(case_id)` or `subscribe_job(job_id)` to get an
   `asyncio.Queue` that receives events filtered by `caseId` or `jobId`.
4. A single payload may carry both `caseId` and `jobId` and will fan out to
   both subscriber sets.

Payload convention (JSON): at least one of `caseId` or `jobId` must be present.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import asyncpg

from src.common.application.logging import get_logger

logger = get_logger(__name__)

CHANNEL = "workflow_document_updated"


class PGNotifier:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._conn: asyncpg.Connection | None = None
        self._case_subscribers: dict[str, set[asyncio.Queue[dict]]] = {}
        self._job_subscribers: dict[str, set[asyncio.Queue[dict]]] = {}
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._conn is not None:
            return
        self._conn = await asyncpg.connect(self._dsn)
        await self._conn.add_listener(CHANNEL, self._on_notify)
        logger.info(f"pg_notifier.started channel={CHANNEL}")

    async def stop(self) -> None:
        if self._conn is None:
            return
        try:
            await self._conn.remove_listener(CHANNEL, self._on_notify)
            await self._conn.close()
        finally:
            self._conn = None
        logger.info(f"pg_notifier.stopped channel={CHANNEL}")

    def _on_notify(self, _conn: Any, _pid: int, _channel: str, payload: str) -> None:
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning(f"pg_notifier.invalid_payload payload={payload!r}")
            return
        case_id = event.get("caseId")
        job_id = event.get("jobId")
        if case_id:
            self._fanout(self._case_subscribers.get(case_id, set()), event, key=f"case:{case_id}")
        if job_id:
            self._fanout(self._job_subscribers.get(job_id, set()), event, key=f"job:{job_id}")

    def _fanout(self, queues: set[asyncio.Queue[dict]], event: dict, key: str) -> None:
        for queue in list(queues):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"pg_notifier.subscriber_queue_full {key}")

    async def subscribe(self, case_id: str) -> asyncio.Queue[dict]:
        return await self._subscribe(self._case_subscribers, case_id)

    async def unsubscribe(self, case_id: str, queue: asyncio.Queue[dict]) -> None:
        await self._unsubscribe(self._case_subscribers, case_id, queue)

    async def subscribe_job(self, job_id: str) -> asyncio.Queue[dict]:
        return await self._subscribe(self._job_subscribers, job_id)

    async def unsubscribe_job(self, job_id: str, queue: asyncio.Queue[dict]) -> None:
        await self._unsubscribe(self._job_subscribers, job_id, queue)

    async def _subscribe(self, bucket: dict[str, set[asyncio.Queue[dict]]], key: str) -> asyncio.Queue[dict]:
        queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=100)
        async with self._lock:
            bucket.setdefault(key, set()).add(queue)
        return queue

    async def _unsubscribe(
        self,
        bucket: dict[str, set[asyncio.Queue[dict]]],
        key: str,
        queue: asyncio.Queue[dict],
    ) -> None:
        async with self._lock:
            subs = bucket.get(key)
            if subs is None:
                return
            subs.discard(queue)
            if not subs:
                bucket.pop(key, None)


def to_asyncpg_dsn(sqlalchemy_dsn: str) -> str:
    """Normalize a SQLAlchemy DSN into a form asyncpg accepts.

    Strips any `+<driver>` suffix (e.g. `postgresql+asyncpg://` → `postgresql://`).
    """
    return re.sub(r"^postgresql\+[a-zA-Z0-9_]+://", "postgresql://", sqlalchemy_dsn)
