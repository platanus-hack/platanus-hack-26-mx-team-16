from dataclasses import dataclass

from src.common.domain.buses.commands import CommandBus
from src.common.domain.buses.events import EventBus
from src.common.domain.buses.queries import QueryBus


@dataclass
class BusContext:
    command_bus: CommandBus
    query_bus: QueryBus
    event_bus: EventBus
