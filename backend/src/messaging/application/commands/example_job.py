from dataclasses import dataclass

from src.common.application.commands.common import ExampleJobCommand
from src.common.application.logging import get_logger
from src.common.domain.buses.commands import CommandHandler

logger = get_logger(__name__)


@dataclass
class ExampleJobHandler(CommandHandler[ExampleJobCommand]):
    """Reference background-job handler (boilerplate D3).

    Runs inside the SAQ worker process. Here it just logs the payload; a real
    job would do work (send a welcome email, generate a report, call an API).
    """

    async def execute(self, command: ExampleJobCommand):
        logger.info("example_job.executed", message=command.message)
