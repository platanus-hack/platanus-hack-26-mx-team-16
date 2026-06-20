from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any

from src.common.domain.entities.common.jtw_session import JwtSession
from src.common.domain.enums.jwt import JwtTokenScope
from src.common.domain.services.token_builder import JwtTokenClaims


class TokenService(ABC):
    @abstractmethod
    async def generate_token(
        self,
        sub: str,
        namespace: str = "JWT",
        extra_claims: dict[str, Any] | None = None,
    ) -> JwtSession:
        raise NotImplementedError

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> tuple[JwtTokenClaims, JwtSession]:
        raise NotImplementedError

    @abstractmethod
    async def get_claims(self, token: str, scope: JwtTokenScope) -> JwtTokenClaims | None:
        raise NotImplementedError

    @abstractmethod
    async def expire_refresh_token(self, refresh_token: str):
        raise NotImplementedError

    @abstractmethod
    async def create_one_shot_token(
        self,
        sub: str,
        scope: JwtTokenScope,
        ttl: timedelta,
        namespace: str = "JWT",
    ) -> str:
        """Issue a single-purpose, short-lived token (no session pair, no
        store). Used for flows like password reset where we want a
        self-contained token that expires by itself."""
        raise NotImplementedError
