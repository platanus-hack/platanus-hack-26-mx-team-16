from dataclasses import dataclass

from src.common.application.queries.users import CheckPasswordQuery
from src.common.domain.buses.queries import QueryHandler
from src.users.domain.repositories.user import UserRepository


@dataclass
class CheckPasswordQueryHandler(QueryHandler[CheckPasswordQuery, bool]):
    user_repository: UserRepository

    async def execute(self, query: CheckPasswordQuery) -> bool:
        return await self.user_repository.check_password(
            user_id=query.user_id,
            raw_password=query.raw_password,
        )
