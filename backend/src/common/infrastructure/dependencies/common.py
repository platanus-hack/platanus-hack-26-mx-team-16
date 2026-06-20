from collections.abc import AsyncGenerator
from typing import Annotated, cast

from saq import Queue
from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client as TemporalClient

from src.common.database.config import DatabaseConfig
from src.common.domain.contexts.bus import BusContext
from src.common.domain.contexts.domain import DomainContext
from src.common.infrastructure.bus_builder import build_async_bus
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.domain_builder import build_async_domain
from src.common.infrastructure.event_publisher import RedisEventPublisher
from src.common.infrastructure.notifications.pg_notifier import PGNotifier


async def get_database_session(request: Request) -> AsyncGenerator[AsyncSession]:
    database_config: DatabaseConfig = request.app.state.database_config
    async with database_config.session_maker() as session:
        request.state.db_session = session
        try:
            yield session
        finally:
            await session.close()


AsyncSessionDep = Annotated[AsyncSession, Depends(get_database_session)]


async def get_domain_context(session: AsyncSessionDep) -> DomainContext:
    return build_async_domain(session=session)


DomainContextDep = Annotated[DomainContext, Depends(get_domain_context)]


def get_task_queue(request: Request) -> Queue:
    return cast("Queue", request.app.state.task_queue)


TaskQueueDep = Annotated[Queue, Depends(get_task_queue)]


def get_temporal_client(request: Request) -> TemporalClient:
    return cast("TemporalClient", request.app.state.temporal_client)


TemporalClientDep = Annotated[TemporalClient, Depends(get_temporal_client)]


def get_pg_notifier(request: Request) -> PGNotifier:
    return cast("PGNotifier", request.app.state.pg_notifier)


PGNotifierDep = Annotated[PGNotifier, Depends(get_pg_notifier)]


def get_redis_client(request: Request) -> Redis:
    return cast("Redis", request.app.state.redis_client)


RedisClientDep = Annotated[Redis, Depends(get_redis_client)]


def get_event_publisher(request: Request) -> RedisEventPublisher:
    return cast("RedisEventPublisher", request.app.state.event_publisher)


EventPublisherDep = Annotated[RedisEventPublisher, Depends(get_event_publisher)]


async def get_bus_context(
    session: AsyncSessionDep,
    domain: DomainContextDep,
    task_queue: TaskQueueDep,
) -> BusContext:
    return build_async_bus(session=session, domain=domain, task_queue=task_queue)


BusContextDep = Annotated[BusContext, Depends(get_bus_context)]


async def get_app_context(
    domain: DomainContextDep,
    bus: BusContextDep,
) -> AppContext:
    return AppContext(domain=domain, bus=bus)
