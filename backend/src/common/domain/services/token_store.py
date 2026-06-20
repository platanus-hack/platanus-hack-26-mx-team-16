from abc import ABC, abstractmethod


class TokenStore(ABC):
    @abstractmethod
    async def store_token(self, sub: str, jti: str, ttl: int, namespace: str):
        raise NotImplementedError

    @abstractmethod
    async def get_token_jti(self, sub: str, namespace: str) -> str | None:
        raise NotImplementedError

    @abstractmethod
    async def blacklist_token_jti(self, jti: str, ttl: int, namespace: str):
        raise NotImplementedError

    @abstractmethod
    async def blacklist_token_sub(self, sub: str, ttl: int, namespace: str):
        raise NotImplementedError

    @abstractmethod
    async def is_blacklisted(self, jti: str, namespace: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def clean(self, jti: str, sub: str, namespace: str) -> bool:
        raise NotImplementedError
