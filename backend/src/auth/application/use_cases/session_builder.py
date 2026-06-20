from dataclasses import dataclass
from uuid import UUID

from src.auth.application.use_cases.mixins import TenantSessionMixin
from src.common.application.queries.users import CheckPasswordQuery, GetUserByEmailQuery
from src.common.domain.buses.queries import QueryBus
from src.common.domain.entities.auth.user_session import TenantUserProfile, TenantUserSession
from src.common.domain.models.user import User
from src.common.domain.exceptions.auth import InvalidCredentialsError
from src.common.domain.exceptions.users import UserNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.services.token_service import TokenService


@dataclass
class TenantUserProfileBuilder(TenantSessionMixin, UseCase):
    user: User
    query_bus: QueryBus

    async def execute(self) -> TenantUserProfile:
        tenant = await self._get_tenant(user_id=self.user.uuid)
        tenant_user = await self._get_tenant_user(user=self.user, tenant=tenant)
        tenant_role = tenant_user.tenant_role_meta if tenant_user else None

        return TenantUserProfile(
            user=self.user,
            tenant=tenant,
            tenant_role=tenant_role,
        )


@dataclass
class TenantUserSessionBuilder(TenantSessionMixin, UseCase):
    email: str
    password: str
    query_bus: QueryBus
    token_service: TokenService

    async def execute(self) -> TenantUserSession:
        user = await self._get_user()
        await self._validate_password(user.uuid)

        jwt_session = await self.token_service.generate_token(
            sub=str(user.uuid),
            namespace="USER",
        )
        params = await self._get_tenant_session_params(user=user)
        return TenantUserSession(
            session=jwt_session,
            user=user,
            tenant=params.tenant,
            tenant_user=params.tenant_user,
            tenant_role=params.tenant_role,
        )

    async def _get_user(self) -> User:
        result = await self.query_bus.ask(
            query=GetUserByEmailQuery(email=self.email),
        )
        if not isinstance(result, User):
            raise UserNotFoundError
        return result

    async def _validate_password(self, user_id: UUID):
        result = await self.query_bus.ask(
            query=CheckPasswordQuery(user_id=user_id, raw_password=self.password),
        )
        if not isinstance(result, bool) or not result:
            raise InvalidCredentialsError
