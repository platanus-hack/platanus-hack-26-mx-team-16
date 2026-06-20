from abc import ABC, abstractmethod

from src.common.domain.entities.phone_number import RawPhoneNumber
from src.common.domain.models.phone_number import PhoneNumber


class PhoneNumberRepository(ABC):
    @abstractmethod
    async def get_or_create(self, phone_number: RawPhoneNumber) -> PhoneNumber:
        raise NotImplementedError
