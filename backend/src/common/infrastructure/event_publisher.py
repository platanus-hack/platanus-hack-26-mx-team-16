"""Generic Redis Pub/Sub event publisher.

Any class that subclasses :class:`Event` (in `src.common.domain.events.base`)
exposes its own `channel`. The publisher is agnostic — it serializes the
envelope and writes to whatever channel the event declares. This lets the
same instance fan out events for cases, workflows, jobs, tenants, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from redis.asyncio import Redis

from src.common.application.logging import get_logger
from src.common.domain.events.base import Event

logger = get_logger(__name__)


class EventPublisher(Protocol):
    async def publish(self, event: Event) -> None: ...


@dataclass
class RedisEventPublisher:
    redis: Redis

    async def publish(self, event: Event) -> None:
        channel = event.channel
        payload = event.model_dump_json()
        await self.redis.publish(channel, payload)
        logger.debug(f"event_publisher.published channel={channel} seq={event.seq}")
