from dataclasses import dataclass

from src.common.domain.buses.commands import Command, CommandBus, CommandHandler


@dataclass
class FakeCommandBus(CommandBus):
    def subscribe(self, command: type[Command], handler: CommandHandler[Command]):
        pass

    async def dispatch_batch(self, commands: list[Command], is_async: bool = False):
        pass

    async def dispatch(self, command: Command, run_async: bool = False):
        pass
