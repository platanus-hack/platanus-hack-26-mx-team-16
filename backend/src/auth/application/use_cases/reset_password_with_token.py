"""Consume a password-reset token and apply the new password."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.enums.jwt import JwtTokenScope
from src.common.domain.exceptions.common import InvalidOrExpiredTokenError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.services.token_service import TokenService
from src.users.domain.repositories.user import UserRepository


@dataclass
class ResetPasswordWithToken(UseCase):
    token: str
    new_password: str
    user_repository: UserRepository
    token_service: TokenService

    async def execute(self) -> None:
        claims = await self.token_service.get_claims(
            self.token,
            scope=JwtTokenScope.PASSWORD_RESET,
        )
        if claims is None:
            raise InvalidOrExpiredTokenError

        try:
            user_id = UUID(claims.sub)
        except (TypeError, ValueError) as exc:
            raise InvalidOrExpiredTokenError from exc

        ok = await self.user_repository.set_password(
            user_id=user_id,
            new_password=self.new_password,
        )
        if not ok:
            raise InvalidOrExpiredTokenError
