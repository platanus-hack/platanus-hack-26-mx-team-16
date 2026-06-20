"""Base class for all domain events that travel over the Redis pub/sub bus.

Each event type owns its own channel; the publisher is agnostic to the type
and only consults `event.channel`. This lets us reuse the same publisher and
SSE infra for any future stream (workflow events, tenant events, etc.).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Event(BaseModel):
    """Generic envelope. Concrete subclasses set `channel` and add fields."""

    seq: int
    ts: datetime
    payload: dict

    model_config = ConfigDict(extra="forbid")

    @property
    def channel(self) -> str:
        raise NotImplementedError("Event subclasses must override the `channel` property")
