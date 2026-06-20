from contextlib import asynccontextmanager

from src.common.application.logging import get_logger
from src.common.domain.entities.common.async_task import AsyncTask

logger = get_logger(__name__)


@asynccontextmanager
async def track_async_task(command_name: str):
    logger.info("async_task.picked_up", command=command_name)
    try:
        yield
    except Exception:
        logger.exception("async_task.infrastructure_error", command=command_name)
        raise


def log_task_result(task_result: AsyncTask) -> None:
    if task_result.is_success:
        logger.info("async_task.completed", operation=task_result.operation, status=task_result.status_label)
    else:
        logger.error(
            "async_task.failed",
            operation=task_result.operation,
            status=task_result.status_label,
            reason=task_result.reason,
        )
