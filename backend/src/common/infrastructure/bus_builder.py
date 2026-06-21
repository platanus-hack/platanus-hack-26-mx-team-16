from redis.asyncio import Redis
from saq import Queue
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.infrastructure.bus_wiring import auth_wiring
from src.common.domain.contexts.bus import BusContext
from src.common.domain.contexts.domain import DomainContext
from src.common.infrastructure.buses import MemoryCommandBus, MemoryEventBus, MemoryQueryBus
from src.common.infrastructure.buses.saq_command_enqueuer import SaqCommandEnqueuer
from src.common.infrastructure.domain_builder import build_async_domain
from src.messaging.infrastructure.bus_wiring import messaging_wiring
from src.scans.infrastructure.bus_wiring import scans_wiring
from src.tenants.infrastructure.bus_wiring import tenants_wiring
from src.users.infrastructure.bus_wiring import users_wiring


def build_async_bus(
    session: AsyncSession,
    domain: DomainContext | None = None,
    task_queue: Queue | None = None,
    redis_client: Redis | None = None,
) -> BusContext:
    domain = domain or build_async_domain(session=session)
    bus = BusContext(
        command_bus=MemoryCommandBus(
            enqueuer=SaqCommandEnqueuer(queue=task_queue),
        ),
        query_bus=MemoryQueryBus(),
        event_bus=MemoryEventBus(),
    )

    auth_wiring(domain, bus)
    messaging_wiring(domain, bus)
    scans_wiring(domain, bus)
    tenants_wiring(domain, bus)
    users_wiring(domain, bus)
    return bus
