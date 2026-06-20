from dataclasses import dataclass

from src.common.application.commands.users import SetUserPasswordCommand
from src.common.application.queries.users import GetUserByIdQuery
from src.common.domain.buses.commands import CommandHandler
from src.common.domain.buses.queries import QueryBus
from src.common.domain.models.user import User
from src.common.domain.exceptions.users import UserNotFoundError
from src.users.domain.repositories.user import UserRepository


@dataclass
class SetUserPasswordHandler(CommandHandler[SetUserPasswordCommand]):
    repository: UserRepository
    query_bus: QueryBus

    async def execute(self, command: SetUserPasswordCommand):
        user: User | None = await self.query_bus.ask(
            query=GetUserByIdQuery(user_id=command.user_id),
        )

        if not user:
            raise UserNotFoundError

        await self.repository.set_password(
            user_id=user.uuid,
            new_password=command.password,
        )
