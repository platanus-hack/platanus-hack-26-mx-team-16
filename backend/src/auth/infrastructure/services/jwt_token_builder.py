from datetime import datetime, timedelta
from uuid import UUID

import pytz
from authlib.jose import JoseError, jwt

from src.auth.domain.services.token_builder import LegacyTokenBuilder
from src.common.application.logging import get_logger

logger = get_logger(__name__)
from src.common.domain.entities.common.jtw_session import JwtSession, JwtTokenClaim
from src.common.domain.models.user import User
from src.common.settings import settings


class LegacyJWTTokenBuilder(LegacyTokenBuilder):
    async def create_access_token(self, user: User) -> JwtSession:
        access_expire = datetime.now(tz=pytz.UTC) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_payload = {
            **user.token_data,
            "exp": access_expire,
            "type": "access",
        }

        access_token_bytes = jwt.encode(
            header={"alg": settings.JWT_ALGORITHM},
            payload=access_payload,
            key=settings.JWT_SECRET_KEY.encode("utf-8"),
        )

        refresh_expire = datetime.now(tz=pytz.UTC) + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)
        refresh_payload = {
            "sub": str(user.uuid),
            "exp": refresh_expire,
            "type": "refresh",
        }

        refresh_token_bytes = jwt.encode(
            header={"alg": settings.JWT_ALGORITHM},
            payload=refresh_payload,
            key=settings.JWT_SECRET_KEY.encode("utf-8"),
        )

        return JwtSession(
            access_token=access_token_bytes.decode("utf-8"),
            refresh_token=refresh_token_bytes.decode("utf-8"),
        )

    def _decode_token(self, token: str, token_type: str) -> JwtTokenClaim | None:
        """Generic method to decode and validate JWT tokens."""
        try:
            claims = jwt.decode(token, settings.JWT_SECRET_KEY.encode("utf-8"))
            claims.validate()

            if token_type == "refresh" and claims.get("type") != token_type:
                logger.error(
                    "jwt.token.invalid",
                    reason="incorrect_token_type",
                    expected_type=token_type,
                    actual_type=claims.get("type"),
                )
                return None

            return JwtTokenClaim(user_id=UUID(claims.get("sub")), exp=claims.get("exp"))
        except JoseError as e:
            logger.error(
                "jwt.token.validation_failed",
                token_type=token_type,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def claim_refresh_token(self, token: str) -> JwtTokenClaim | None:
        return self._decode_token(token, "refresh")

    async def claim_access_token(self, token: str) -> JwtTokenClaim | None:
        return self._decode_token(token, "access")
