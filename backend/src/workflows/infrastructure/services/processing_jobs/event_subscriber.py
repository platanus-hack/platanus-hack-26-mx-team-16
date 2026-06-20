"""Async-iterator over the Redis pubsub channel for processing-job events.

Wraps the redis-py ``pubsub`` API into a single coroutine the endpoint can
``async for`` over. Heartbeats are emitted every ``heartbeat_seconds`` of
silence so the EventSource on the browser doesn't time out behind a proxy.
The endpoint is responsible for translating the yielded raw dicts into
the SSE wire format.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from redis.asyncio import Redis

from src.common.application.logging import get_logger
from src.workflows.domain.events import processing_job_channel

logger = get_logger(__name__)

HEARTBEAT_PAYLOAD: dict = {"_heartbeat": True}


@dataclass
class ProcessingJobEventSubscriber:
    """Async source of live events for a single workflow's processing-jobs."""

    redis_client: Redis
    workflow_id: UUID
    heartbeat_seconds: float = 20.0

    async def stream(self) -> AsyncIterator[dict | None]:
        """Yield event dicts as they arrive on Redis. ``None`` is yielded as a
        heartbeat tick when the channel is silent for ``heartbeat_seconds``."""
        channel = processing_job_channel(self.workflow_id)
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(channel)
        try:
            while True:
                try:
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=self.heartbeat_seconds,
                    )
                except asyncio.TimeoutError:
                    yield None
                    continue
                if message is None:
                    yield None
                    continue
                payload = message.get("data")
                if not isinstance(payload, str):
                    continue
                try:
                    yield json.loads(payload)
                except json.JSONDecodeError:
                    logger.warning(f"processing_job_events.invalid_payload channel={channel} payload={payload!r}")
                    continue
        finally:
            try:
                await pubsub.unsubscribe(channel)
            finally:
                await pubsub.aclose()
