from dataclasses import dataclass

from src.common.domain.models.user import User
from src.common.domain.interfaces.use_case import UseCase
from src.users.domain.exceptions import InvalidUserAuthError, UserAlreadyExistError
from src.users.domain.repositories.user import UserRepository


@dataclass
class UserRegisterer(UseCase):
    user: User
    password: str
    user_repository: UserRepository
    is_superuser: bool = False

    async def execute(self) -> User:
        if not self.user.email_address:
            raise InvalidUserAuthError

        existing_user = await self.user_repository.find_by_email(self.user.email_address.email)
        if existing_user:
            raise UserAlreadyExistError

        return await self.user_repository.create_user(
            user=self.user,
            password=self.password,
            is_superuser=self.is_superuser,
        )
