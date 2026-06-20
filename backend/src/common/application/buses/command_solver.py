import logging
import traceback
from dataclasses import dataclass

from src.common.application.data.tasks_mapping import async_tasks_mapping
from src.common.domain.buses.commands import Command, CommandBus
from src.common.domain.entities.common.async_task import AsyncTask
from src.common.domain.interfaces.use_case import UseCase
from src.common.infrastructure.buses.meta_command import MetaCommand


@dataclass
class AsyncTaskResolver(UseCase):
    command_bus: CommandBus
    payload: dict

    async def execute(self) -> AsyncTask:
        meta_command = MetaCommand.from_dict(self.payload)
        try:
            command_class: type[Command] | None = async_tasks_mapping.get(meta_command.command_name)
            if not command_class:
                logging.error(
                    "AsyncTaskResolver: error=CommandNotFound command=%s",
                    meta_command.command_name,
                )
                return AsyncTask(
                    operation=meta_command.command_name,
                    is_success=False,
                    reason="NotRegisteredCommand",
                )
            await self.command_bus.dispatch(
                command=command_class.from_dict(meta_command.payload),
            )
            return AsyncTask(
                operation=meta_command.command_name,
                is_success=True,
            )
        except Exception as e:
            logging.error(
                "AsyncTaskResolver: %s\nTraceback:\n%s",
                e,
                traceback.format_exc(),
            )
            return AsyncTask(
                operation=meta_command.command_name,
                is_success=False,
            )
