from abc import ABC, abstractmethod

from src.common.domain.entities.common.jtw_session import JwtSession, JwtTokenClaim
from src.common.domain.models.user import User


class LegacyTokenBuilder(ABC):
    @abstractmethod
    async def create_access_token(self, user: User) -> JwtSession:
        raise NotImplementedError

    @abstractmethod
    async def claim_refresh_token(self, token: str) -> JwtTokenClaim | None:
        raise NotImplementedError

    @abstractmethod
    async def claim_access_token(self, token: str) -> JwtTokenClaim | None:
        raise NotImplementedError
