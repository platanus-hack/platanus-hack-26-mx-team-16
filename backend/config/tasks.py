from typing import Any

from redis.asyncio import Redis
from saq import CronJob, Queue

from src.common.application.buses.command_solver import AsyncTaskResolver
from src.common.application.helpers.task_tracker import log_task_result, track_async_task
from src.common.application.logging import get_logger
from src.common.database.config import DatabaseConfig, get_database_config
from src.common.domain.enums.scans import ScanLevel
from src.common.infrastructure.bus_builder import build_async_bus
from src.common.infrastructure.domain_builder import build_async_domain
from src.common.settings import settings
from src.scans.application.commands.monitor_cron import MonitorCronHandler

logger = get_logger()

queue = Queue.from_url(settings.redis_url)


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("Starting workers...")
    ctx["db_config"] = get_database_config()
    ctx["redis"] = Redis.from_url(settings.redis_url, decode_responses=True, encoding="utf-8")


async def shutdown(ctx: dict[str, Any]) -> None:
    await ctx["db_config"].dispose()
    redis = ctx.get("redis")
    if redis is not None:
        await redis.aclose()
    logger.info("Closing workers...")


async def handle_command(ctx: dict[str, Any], *, command_data: dict[str, Any]) -> None:
    command_name = command_data.get("command_name", "unknown")
    database_config: DatabaseConfig = ctx["db_config"]
    async with track_async_task(command_name):
        async with database_config.session_maker() as session:
            bus = build_async_bus(
                session=session,
                domain=build_async_domain(session=session),
                redis_client=ctx.get("redis"),
            )
            task_result = await AsyncTaskResolver(
                command_bus=bus.command_bus,
                payload=command_data,
            ).execute()
        log_task_result(task_result)


async def monitor_cron(ctx: dict[str, Any]) -> None:
    """SAQ ``CronJob`` body (08-ranking-watchlists §4.1).

    Re-enqueues every ``watchlist.monitor=true`` site + every gov seed site
    through the idempotent automatic-enqueue (same partial-unique-index contract
    as ``POST /scans``). Builds its own session/bus from ``ctx`` like
    ``handle_command``; the cron only enqueues — execution and alert evaluation
    happen downstream.
    """
    database_config: DatabaseConfig = ctx["db_config"]
    async with track_async_task("monitor_cron"):
        async with database_config.session_maker() as session:
            domain = build_async_domain(session=session)
            bus = build_async_bus(
                session=session,
                domain=domain,
                task_queue=queue,
                redis_client=ctx.get("redis"),
            )
            level_default = ScanLevel(
                getattr(settings, "MONITOR_LEVEL_DEFAULT", "basico")
            )
            await MonitorCronHandler(
                site_repository=domain.site_repository,
                watchlist_repository=domain.watchlist_repository,
                scan_repository=domain.scan_repository,
                command_bus=bus.command_bus,
                monitor_level_default=level_default,
            ).execute()


# Launch with:  saq config.tasks.worker_settings
worker_settings = {
    "queue": queue,
    "functions": [handle_command, monitor_cron],
    "cron_jobs": [
        CronJob(monitor_cron, cron=getattr(settings, "MONITOR_CRON", "0 */6 * * *")),
    ],
    "startup": startup,
    "shutdown": shutdown,
}
