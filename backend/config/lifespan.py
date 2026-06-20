from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI
from redis.asyncio import Redis
from saq import Queue
from temporalio.client import Client as TemporalClient
from temporalio.contrib.pydantic import pydantic_data_converter

from src.common.application.logging import get_logger
from src.common.database.config import get_database_config
from src.common.infrastructure.event_publisher import RedisEventPublisher
from src.common.infrastructure.notifications.pg_notifier import (
    PGNotifier,
    to_asyncpg_dsn,
)
from src.common.settings import settings
from src.workflows.infrastructure.services.rules.bootstrap import register_default_kinds

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --------- STARTUP ----------
    register_default_kinds()
    database_config = get_database_config()

    redis_client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        encoding="utf-8",
    )

    logger.info("saq.queue.initializing")
    task_queue = Queue.from_url(settings.redis_url)
    await task_queue.connect()
    logger.info("saq.queue.ready")

    logger.info("temporal.client.initializing")
    temporal_client = await TemporalClient.connect(
        settings.TEMPORAL_HOST,
        data_converter=pydantic_data_converter,
    )
    logger.info("temporal.client.ready")

    # PGNotifier is kept around for any remaining LISTEN/NOTIFY consumers
    # (e.g. legacy SINGLE-document drop-zone pipeline). The case-detail
    # live feed runs over Redis Pub/Sub via `event_publisher`.
    pg_notifier = PGNotifier(dsn=to_asyncpg_dsn(str(settings.async_database_url)))
    await pg_notifier.start()

    event_publisher = RedisEventPublisher(redis=redis_client)

    app_with_context = cast("Any", app)
    app_with_context.state.database_config = database_config
    app_with_context.state.redis_client = redis_client
    app_with_context.state.task_queue = task_queue
    app_with_context.state.temporal_client = temporal_client
    app_with_context.state.pg_notifier = pg_notifier
    app_with_context.state.event_publisher = event_publisher

    yield

    # --------- SHUTDOWN ----------
    logger.info("saq.queue.closing")
    await task_queue.disconnect()
    logger.info("saq.queue.closed")

    await pg_notifier.stop()
    await database_config.dispose()
    await redis_client.aclose()
