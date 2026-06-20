from abc import ABC, abstractmethod

from src.common.domain.models.email_address import EmailAddress


class EmailAddressRepository(ABC):
    @abstractmethod
    async def get_or_create(self, email: str) -> EmailAddress:
        raise NotImplementedError
