import uuid
from dataclasses import dataclass

from src.common.application.queries.users import (
    GetOrCreateUserQuery,
    GetUserByEmailQuery,
    GetUserByIdQuery,
    GetUserByPhoneNumberQuery,
)
from src.common.domain.buses.queries import QueryBus, QueryHandler
from src.common.domain.models.user import User
from src.users.domain.repositories.email_address import EmailAddressRepository
from src.users.domain.repositories.user import UserRepository


@dataclass
class GetOrCreateUserHandler(QueryHandler[GetOrCreateUserQuery, User]):
    email_repository: EmailAddressRepository
    user_repository: UserRepository
    query_bus: QueryBus

    async def execute(self, query: GetOrCreateUserQuery) -> User | None:
        if query.email:
            return await self._build_from_email(
                email=query.email,
                first_name=query.first_name,
                last_name=query.last_name,
            )

        raise NotImplementedError

    async def _build_from_email(
        self,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User | None:
        user = await self.user_repository.find_by_email(email)

        if user:
            return user

        email_address = await self.email_repository.get_or_create(email=email)
        return await self.user_repository.persist(
            instance=User(
                uuid=uuid.uuid4(),
                username=uuid.uuid4().hex,
                first_name=first_name,
                last_name=last_name,
                email_address=email_address,
            ),
        )


@dataclass
class GetUserByIdHandler(QueryHandler[GetUserByIdQuery, User]):
    user_repository: UserRepository

    async def execute(self, query: GetUserByIdQuery) -> User | None:
        return await self.user_repository.find(query.user_id)


@dataclass
class GetUserByEmailHandler(QueryHandler[GetUserByEmailQuery, User]):
    user_repository: UserRepository

    async def execute(self, query: GetUserByEmailQuery) -> User | None:
        return await self.user_repository.find_by_email(query.email)


@dataclass
class GetUserByPhoneNumberHandler(QueryHandler[GetUserByPhoneNumberQuery, User]):
    user_repository: UserRepository

    async def execute(self, query: GetUserByPhoneNumberQuery) -> User | None:
        return await self.user_repository.find_by_phone_number(query.phone_number)
