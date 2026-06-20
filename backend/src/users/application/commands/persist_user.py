from dataclasses import dataclass

from src.common.application.commands.users import PersistUserCommand
from src.common.domain.buses.commands import CommandHandler
from src.users.domain.repositories.user import UserRepository


@dataclass
class PersistUserHandler(CommandHandler[PersistUserCommand]):
    user_repository: UserRepository

    async def execute(self, command: PersistUserCommand):
        await self.user_repository.persist(
            instance=command.user,
        )
