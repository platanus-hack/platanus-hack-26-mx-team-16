from dataclasses import dataclass

from src.common.application.commands.users import UpdateUserPasswordCommand
from src.common.domain.buses.commands import CommandHandler
from src.common.domain.exceptions.auth import InvalidCredentialsError
from src.users.domain.repositories.user import UserRepository


@dataclass
class UpdateUserPasswordHandler(CommandHandler[UpdateUserPasswordCommand]):
    user_repository: UserRepository

    async def execute(self, command: UpdateUserPasswordCommand):
        if not await self.user_repository.check_password(
            user_id=command.user_id,
            raw_password=command.current_password,
        ):
            raise InvalidCredentialsError

        await self.user_repository.set_password(
            user_id=command.user_id,
            new_password=command.new_password,
        )
