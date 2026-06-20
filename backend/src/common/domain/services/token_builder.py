from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any

from src.common.domain.enums.jwt import JwtTokenScope
from src.common.domain.mixins.entities import CamelModel


class JwtTokenClaims(CamelModel):
    iss: str
    sub: str
    iat: int
    exp: int
    jti: str
    ns: str
    scope: JwtTokenScope


class TokenBuilder(ABC):
    @abstractmethod
    def create_token(
        self,
        sub: str,
        scope: JwtTokenScope,
        exp_delta: timedelta,
        namespace: str = "JWT",
        jti: str | None = None,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify_token(
        self,
        token: str,
        expected_scope: JwtTokenScope,
    ) -> JwtTokenClaims | None:
        raise NotImplementedError
