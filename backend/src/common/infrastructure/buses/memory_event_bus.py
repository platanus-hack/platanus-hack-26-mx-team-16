from collections import defaultdict

from src.common.domain.buses.events import DomainEvent, DomainEventHandler, EventBus
from src.common.infrastructure.buses._exceptions import EventHandlerDoesNotExistError


class MemoryEventBus(EventBus):
    def __init__(self) -> None:
        self._events: dict[type[DomainEvent], list[DomainEventHandler]] = defaultdict(list)

    def subscribe(self, event: type[DomainEvent], handler: DomainEventHandler) -> None:
        self._events[event].append(handler)

    def publish_batch(self, events: list[DomainEvent]) -> None:
        self.publish(events)

    def publish(self, events: list[DomainEvent]) -> None:
        for event in events:
            if event.__class__ not in self._events:
                raise EventHandlerDoesNotExistError

            for event_handler in self._events[event.__class__]:
                event_handler.execute(event)
