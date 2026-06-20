from datetime import datetime, timezone

from expects import equal, expect, raise_error

from src.common.domain.events.base import Event


def _build_event() -> Event:
    return Event(
        seq=1,
        ts=datetime(2026, 4, 28, tzinfo=timezone.utc),
        payload={"hello": "world"},
    )


def test_channel__base_class_raises_not_implemented():
    event = _build_event()

    expect(lambda: event.channel).to(raise_error(NotImplementedError))


def test_payload__roundtrips_dict():
    event = _build_event()

    expect(event.payload).to(equal({"hello": "world"}))
