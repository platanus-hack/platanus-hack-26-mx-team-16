from datetime import UTC, datetime, timedelta
from typing import Any

from authlib.jose import JoseError, jwt
from uuid6 import uuid7

from src.common.application.logging import get_logger
from src.common.domain.enums.jwt import JwtTokenScope
from src.common.domain.services.token_builder import JwtTokenClaims, TokenBuilder

logger = get_logger(__name__)
from src.common.settings import settings


class JwtTokenBuilder(TokenBuilder):
    def create_token(
        self,
        sub: str,
        scope: JwtTokenScope,
        exp_delta: timedelta,
        namespace: str = "JWT",
        jti: str | None = None,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        jti = jti or uuid7().hex
        claims = self._build_claims(
            sub=sub,
            jti=jti,
            scope=str(scope),
            exp_delta=exp_delta,
            ns=namespace,
        )
        if extra_claims:
            # Generic extra claims; reserved base-contract claims are never overwritten.
            claims.update({k: v for k, v in extra_claims.items() if k not in claims})
        return jwt.encode(
            header={"alg": settings.JWT_ALGORITHM},
            payload=claims,
            key=settings.JWT_SECRET_KEY.encode("utf-8"),
        ).decode()

    def verify_token(
        self,
        token: str,
        expected_scope: JwtTokenScope,
    ) -> JwtTokenClaims | None:
        try:
            claims = jwt.decode(token, key=settings.JWT_SECRET_KEY.encode("utf-8"))
            if claims["scope"] != str(expected_scope):
                logger.error(
                    "jwt.token.scope_mismatch",
                    expected_scope=str(expected_scope),
                    actual_scope=claims.get("scope"),
                )
                return None
            claims.validate(now=int(datetime.now(UTC).timestamp()))
            return JwtTokenClaims.model_validate(claims)
        except JoseError as e:
            logger.error(
                "jwt.token.invalid",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    @classmethod
    def _build_claims(
        cls,
        sub: str,
        exp_delta: timedelta,
        jti: str,
        scope: str,
        ns: str = "JWT",
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        return {
            "iss": settings.JWT_ISSUER,
            "sub": sub,
            "iat": int(now.timestamp()),
            "exp": int((now + exp_delta).timestamp()),
            "jti": jti,
            "ns": ns,
            "scope": scope,  # access | refresh
        }
