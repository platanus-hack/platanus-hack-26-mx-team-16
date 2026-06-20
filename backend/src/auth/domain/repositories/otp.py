from abc import ABC, abstractmethod


class OTPRepository(ABC):
    @abstractmethod
    def save_otp(self, phone: str, otp: str, ttl: int) -> None: ...

    @abstractmethod
    def get_otp(self, phone: str) -> str | None: ...

    @abstractmethod
    def verify_otp(self, phone: str, otp: str) -> bool: ...

    @abstractmethod
    def delete_otp(self, phone: str) -> None: ...
