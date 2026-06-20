from dataclasses import dataclass

from src.common.application.logging import get_logger
from src.common.domain.buses.async_commands import CommandEnqueuer

logger = get_logger(__name__)
from src.common.domain.buses.commands import Command, CommandBus, CommandHandler
from src.common.infrastructure.buses._exceptions import (
    CommandAlreadyExistError,
    CommandHandlerDoesNotExistError,
)


@dataclass
class MemoryCommandBus(CommandBus):
    enqueuer: CommandEnqueuer

    def __post_init__(self):
        self._commands: dict[type[Command], CommandHandler[Command]] = {}

    def subscribe(self, command: type[Command], handler: CommandHandler[Command]):
        if command in self._commands:
            raise CommandAlreadyExistError
        self._commands[command] = handler

    async def dispatch(
        self,
        command: Command,
        run_async: bool = False,
    ):
        if command.__class__ not in self._commands:
            raise CommandHandlerDoesNotExistError(command.__class__)

        if run_async:
            logger.info(
                "command_bus.async_dispatch",
                command=command.__class__.__name__,
            )
            await self.enqueuer.enqueue(command)
            return
        await self._commands[command.__class__].execute(command)
