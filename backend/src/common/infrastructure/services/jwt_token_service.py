from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from uuid6 import uuid7

from src.common.application.logging import get_logger
from src.common.domain.entities.common.jtw_session import JwtSession

logger = get_logger(__name__)
from src.common.domain.exceptions.common import InvalidOrExpiredRefreshTokenError
from src.common.domain.enums.jwt import JwtTokenScope
from src.common.domain.services.token_builder import JwtTokenClaims, TokenBuilder
from src.common.domain.services.token_service import TokenService
from src.common.domain.services.token_store import TokenStore
from src.common.settings import settings
from src.staff.domain.repositories.staff_user import StaffUserRepository


@dataclass
class JwtTokenService(TokenService):
    token_store: TokenStore
    token_builder: TokenBuilder
    # ADR 0001: re-derivación de `is_staff` en el refresh — el refresh
    # reconstruye claims solo desde `sub`, así que sin lookup el claim
    # moriría al primer refresh del access token.
    staff_user_repository: StaffUserRepository | None = None

    async def generate_token(
        self,
        sub: str,
        namespace: str = "JWT",
        extra_claims: dict[str, Any] | None = None,
    ) -> JwtSession:
        await self.token_store.blacklist_token_sub(
            sub=sub,
            ttl=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES * 60,
            namespace=namespace,
        )

        access_token_jti = uuid7().hex
        refresh_token_jti = uuid7().hex

        access_token = self.token_builder.create_token(
            jti=access_token_jti,
            sub=sub,
            scope=JwtTokenScope.ACCESS,
            exp_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            namespace=namespace,
            extra_claims=extra_claims,
        )
        refresh_token = self.token_builder.create_token(
            jti=refresh_token_jti,
            sub=sub,
            scope=JwtTokenScope.REFRESH,
            exp_delta=timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES),
            namespace=namespace,
        )
        await self.token_store.store_token(
            jti=refresh_token_jti,
            sub=sub,
            ttl=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES * 60,
            namespace=namespace,
        )

        return JwtSession(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh_token(self, refresh_token: str) -> tuple[JwtTokenClaims, JwtSession]:
        claims = self.token_builder.verify_token(
            token=refresh_token,
            expected_scope=JwtTokenScope.REFRESH,
        )

        if not claims:
            raise InvalidOrExpiredRefreshTokenError

        if await self.token_store.is_blacklisted(jti=claims.jti, namespace=claims.ns):
            logger.warning(
                "jwt.token.blacklisted",
                jti=claims.jti,
                sub=claims.sub,
                namespace=claims.ns,
            )
            raise InvalidOrExpiredRefreshTokenError

        # Rotation
        await self.token_store.blacklist_token_sub(
            sub=claims.sub,
            ttl=self._get_exp_remaining_seconds(claims.exp),
            namespace=claims.ns,
        )

        access_token_jti = uuid7().hex
        refresh_token_jti = uuid7().hex

        access_token = self.token_builder.create_token(
            jti=access_token_jti,
            sub=claims.sub,
            scope=JwtTokenScope.ACCESS,
            exp_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            # ADR 0001: el refresh re-deriva `is_staff` desde la fila viva
            # (el claim solo gatea; la fila activa es la fuente de verdad).
            extra_claims=await self._derive_staff_claims(claims.sub),
        )
        refresh_token = self.token_builder.create_token(
            jti=refresh_token_jti,
            sub=claims.sub,
            scope=JwtTokenScope.REFRESH,
            exp_delta=timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES),
        )

        await self.token_store.store_token(
            jti=refresh_token_jti,
            sub=claims.sub,
            ttl=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES * 60,
            namespace=claims.ns,
        )
        return claims, JwtSession(access_token=access_token, refresh_token=refresh_token)

    async def get_claims(self, token: str, scope: JwtTokenScope) -> JwtTokenClaims | None:
        return self.token_builder.verify_token(
            token=token,
            expected_scope=scope,
        )

    async def create_one_shot_token(
        self,
        sub: str,
        scope: JwtTokenScope,
        ttl: timedelta,
        namespace: str = "JWT",
    ) -> str:
        return self.token_builder.create_token(
            sub=sub,
            scope=scope,
            exp_delta=ttl,
            namespace=namespace,
        )

    async def expire_refresh_token(self, refresh_token: str):
        jwt_claims = await self.get_claims(refresh_token, scope=JwtTokenScope.REFRESH)
        await self.token_store.blacklist_token_sub(
            sub=jwt_claims.sub,
            ttl=self._get_exp_remaining_seconds(jwt_claims.exp),
            namespace=jwt_claims.ns,
        )
        await self.token_store.clean(
            jti=jwt_claims.jti,
            sub=jwt_claims.sub,
            namespace=jwt_claims.ns,
        )

    async def _derive_staff_claims(self, sub: str) -> dict[str, Any] | None:
        if self.staff_user_repository is None:
            return None
        try:
            user_id = UUID(sub)
        except ValueError:
            return None
        staff_user = await self.staff_user_repository.find_active_by_user_id(user_id)
        return {"is_staff": True} if staff_user is not None else None

    @classmethod
    def _get_exp_remaining_seconds(cls, exp: int) -> int:
        return max(exp - int(datetime.now(UTC).timestamp()), 0)
