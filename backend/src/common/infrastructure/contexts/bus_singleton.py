from src.common.application.helpers.singleton import SingletonMeta
from src.common.domain.contexts.bus import BusContext
from src.common.infrastructure.buses import MemoryCommandBus, MemoryEventBus, MemoryQueryBus
from src.common.infrastructure.buses.saq_command_enqueuer import SaqCommandEnqueuer


class BusSingleton(metaclass=SingletonMeta):
    instance: BusContext = BusContext(
        command_bus=MemoryCommandBus(
            enqueuer=SaqCommandEnqueuer(),
        ),
        query_bus=MemoryQueryBus(),
        event_bus=MemoryEventBus(),
    )
