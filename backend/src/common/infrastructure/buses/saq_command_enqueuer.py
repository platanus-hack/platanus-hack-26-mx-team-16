from dataclasses import dataclass, field

from saq import Queue

from src.common.application.logging import get_logger
from src.common.constants import AWS_LAMBDA_MAX_TIMEOUT
from src.common.domain.buses.async_commands import CommandEnqueuer
from src.common.domain.buses.commands import Command
from src.common.infrastructure.buses.meta_command import MetaCommand
from src.common.settings import settings

logger = get_logger(__name__)


@dataclass
class SaqCommandEnqueuer(CommandEnqueuer):
    """Enqueues commands to SAQ (Simple Async Queue) for background processing.

    Reuses a shared :class:`saq.Queue` (set by the app lifespan) when provided;
    otherwise it creates and tears down a temporary connection per command.
    """

    queue: Queue | None = None
    redis_url: str = field(default_factory=lambda: settings.redis_url)

    async def enqueue(self, command: Command) -> None:
        command_name = command.__class__.__name__
        meta_command = MetaCommand.from_command(command)

        queue = self.queue
        owns_queue = queue is None
        if owns_queue:
            queue = Queue.from_url(self.redis_url)
            await queue.connect()
            logger.debug("saq.using_temporary_queue", command=command_name)
        else:
            logger.debug("saq.using_shared_queue", command=command_name)

        try:
            job = await queue.enqueue("handle_command", command_data=meta_command.to_dict, timeout=AWS_LAMBDA_MAX_TIMEOUT)
            if job is None:
                logger.error("saq.command.enqueue_failed", command=command_name)
                msg = f"Failed to enqueue command {command_name}"
                raise RuntimeError(msg)
            logger.info("saq.command.enqueued", job=job.key, command=command_name)
        except Exception as e:
            logger.error(
                "saq.command.enqueue_error",
                command=command_name,
                error=str(e),
                error_type=e.__class__.__name__,
            )
            raise
        finally:
            if owns_queue:
                await queue.disconnect()
