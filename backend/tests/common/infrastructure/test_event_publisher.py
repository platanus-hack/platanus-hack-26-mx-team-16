"""RedisEventPublisher contract: it MUST publish on the channel the
event self-declares, with the JSON envelope serialized via
``model_dump_json``. The publisher is intentionally agnostic to the
event type — these tests pin that abstraction in place.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from expects import contain, equal, expect

from src.common.domain.events.base import Event
from src.common.infrastructure.event_publisher import RedisEventPublisher


class _FakeEvent(Event):
    """Concrete event whose channel is a constant we can assert on."""

    @property
    def channel(self) -> str:
        return "test:fake:events"


@pytest.fixture
def fake_event():
    return _FakeEvent(
        seq=42,
        ts=datetime(2026, 5, 4, 12, 0, tzinfo=UTC),
        payload={"hello": "world"},
    )


@pytest.fixture
def redis_mock():
    redis = MagicMock()
    redis.publish = AsyncMock()
    return redis


async def test_publish__writes_to_event_channel(redis_mock, fake_event):
    publisher = RedisEventPublisher(redis=redis_mock)

    await publisher.publish(fake_event)

    expect(redis_mock.publish.await_args.args[0]).to(equal("test:fake:events"))


async def test_publish__serializes_envelope_as_json(redis_mock, fake_event):
    publisher = RedisEventPublisher(redis=redis_mock)

    await publisher.publish(fake_event)

    payload = redis_mock.publish.await_args.args[1]
    expect(payload).to(contain('"seq":42'))
    expect(payload).to(contain('"hello":"world"'))


async def test_publish__sends_one_message_per_event(redis_mock, fake_event):
    publisher = RedisEventPublisher(redis=redis_mock)

    await publisher.publish(fake_event)
    await publisher.publish(fake_event)

    expect(redis_mock.publish.await_count).to(equal(2))
