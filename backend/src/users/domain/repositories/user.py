from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.entities.phone_number import RawPhoneNumber
from src.common.domain.models.user import User


class UserRepository(ABC):
    @abstractmethod
    async def find(self, user_id: UUID) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_phone_number(self, phone_number: RawPhoneNumber) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_email(self, email: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def check_password(self, user_id: UUID, raw_password: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def set_password(self, user_id: UUID, new_password: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def filter(self) -> list[User]:
        raise NotImplementedError

    @abstractmethod
    async def persist(self, instance: User) -> User:
        raise NotImplementedError

    @abstractmethod
    async def remove(self, user_id: UUID):
        raise NotImplementedError

    @abstractmethod
    async def update_current_tenant(self, user_id: UUID, tenant_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create_user(self, user: User, password: str, is_superuser: bool = False) -> User:
        raise NotImplementedError

    @abstractmethod
    async def clear_current_tenant_for_users(self, tenant_id: UUID) -> None:
        raise NotImplementedError
