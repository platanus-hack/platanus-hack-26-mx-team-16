from uuid import UUID

from src.common.domain.mixins.entities import CamelModel


class JwtTokenClaim(CamelModel):
    user_id: UUID
    exp: int


class JwtSession(CamelModel):
    access_token: str
    refresh_token: str
