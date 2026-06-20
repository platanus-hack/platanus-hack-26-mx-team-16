from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class DomainEvent(ABC):
    id: UUID
    timestamp: datetime
    args: tuple[Any, ...] | None = None


class DomainEventHandler(ABC):
    @abstractmethod
    def execute(self, event: DomainEvent):
        raise NotImplementedError


class EventBus(ABC):
    @abstractmethod
    def subscribe(self, event: type[DomainEvent], handler: DomainEventHandler):
        raise NotImplementedError

    @abstractmethod
    def publish_batch(self, event: list[DomainEvent]):
        raise NotImplementedError

    @abstractmethod
    def publish(self, events: list[DomainEvent]):
        raise NotImplementedError
