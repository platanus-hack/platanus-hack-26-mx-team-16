from typing import Any
from uuid import UUID

from src.common.application.queries.users import (
    GetUserByEmailQuery,
    GetUserByPhoneNumberQuery,
)
from src.common.domain.buses.queries import QueryBus
from src.common.domain.entities.phone_number import RawPhoneNumber
from src.common.domain.models.user import User
from src.common.domain.exceptions.users import (
    UserEmailAlreadyExistsError,
    UserPhoneNumberAlreadyExistsError,
)


class UserEmailPhoneNumberMixin:
    query_bus: QueryBus

    async def _get_user_by_email(self, email: str) -> User | None:
        result = await self.query_bus.ask(query=GetUserByEmailQuery(email=email))
        return result if isinstance(result, (User, type(None))) else None

    async def _get_user_by_phone_number(self, phone_number: RawPhoneNumber) -> User | None:
        result = await self.query_bus.ask(query=GetUserByPhoneNumberQuery(phone_number=phone_number))
        return result if isinstance(result, (User, type(None))) else None

    async def assert_email_is_unique(self, email: str, current_user_id: UUID | None = None):
        existing_user = await self._get_user_by_email(email)
        if existing_user and (current_user_id is None or existing_user.uuid != current_user_id):
            raise UserEmailAlreadyExistsError

    async def assert_phone_number_is_unique(
        self,
        phone_number: RawPhoneNumber | None,
        current_user_id: UUID | None = None,
    ) -> None:
        if phone_number is None:
            return

        existing_user = await self._get_user_by_phone_number(phone_number)
        if existing_user and (current_user_id is None or existing_user.uuid != current_user_id):
            raise UserPhoneNumberAlreadyExistsError

    @classmethod
    def _build_phone_number(
        cls,
        phone_number: RawPhoneNumber | dict[str, Any],
    ) -> RawPhoneNumber | None:
        if phone_number is None:
            return None
        if isinstance(phone_number, RawPhoneNumber):
            return phone_number
        return RawPhoneNumber.model_validate(phone_number)
