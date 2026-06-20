from dataclasses import dataclass
from uuid import UUID

from src.common.domain.entities.auth.google_login import GoogleAuthTokens, GoogleUser
from src.common.application.queries.tenants import GetUserTenantQuery
from src.common.application.queries.users import GetOrCreateUserQuery
from src.common.domain.buses.queries import QueryBus
from src.common.domain.entities.auth.user_session import TenantUserSession
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.user import User
from src.common.domain.exceptions.auth import InvalidGoogleIdTokenError, RetrieveGoogleUserError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.services.token_service import TokenService


@dataclass
class GoogleSessionBuilder(UseCase):
    google_tokens: GoogleAuthTokens
    google_user: GoogleUser | None
    query_bus: QueryBus
    token_service: TokenService

    async def execute(self) -> TenantUserSession:
        if not self.google_user:
            raise InvalidGoogleIdTokenError

        user: User | None = await self.query_bus.ask(
            query=GetOrCreateUserQuery(
                email=self.google_user.email,
                first_name=self.google_user.given_name,
                last_name=self.google_user.family_name,
                picture=self.google_user.picture,
            )
        )

        if not isinstance(user, User):
            raise RetrieveGoogleUserError

        jwt_session = await self.token_service.generate_token(
            sub=str(user.uuid),
            namespace="USER",
        )
        tenant = await self._get_tenant(user_id=user.uuid)

        return TenantUserSession(
            session=jwt_session,
            user=user,
            tenant=tenant,
        )

    async def _get_tenant(self, user_id: UUID) -> Tenant | None:
        return await self.query_bus.ask(
            query=GetUserTenantQuery(user_id),
        )
