from dataclasses import dataclass

from uuid6 import UUID

from src.auth.application.use_cases.mixins import TenantSessionMixin
from src.auth.domain.exceptions import InvalidRefreshTokenError
from src.common.application.queries.users import GetUserByIdQuery
from src.common.domain.buses.queries import QueryBus
from src.common.domain.entities.auth.user_session import TenantUserSession
from src.common.domain.models.user import User
from src.common.domain.exceptions.users import UserNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.services.token_service import TokenService
from src.staff.domain.repositories.staff_user import StaffUserRepository


@dataclass
class TenantUserRefreshSessionBuilder(TenantSessionMixin, UseCase):
    refresh_token: str
    query_bus: QueryBus
    token_service: TokenService
    # E5 · ADR 0001: el refresh es la fuente del user en cada page-load del
    # FE (ProtectedLayout / layout staff) — sin esto `isStaff` moriría al
    # recargar. El claim del JWT se re-deriva aparte en JwtTokenService.
    staff_user_repository: StaffUserRepository | None = None

    async def execute(self) -> TenantUserSession:
        await self._validate_refresh_token()
        jwt_claims, jwt_session = await self.token_service.refresh_token(self.refresh_token)

        user = await self._get_user(UUID(jwt_claims.sub))
        params = await self._get_tenant_session_params(user=user)
        staff_user = await self._find_staff_user(user.uuid)

        return TenantUserSession(
            session=jwt_session,
            user=user,
            tenant=params.tenant,
            tenant_user=params.tenant_user,
            tenant_role=params.tenant_role,
            is_staff=staff_user is not None,
            staff_role=staff_user.role.value if staff_user is not None else None,
        )

    async def _find_staff_user(self, user_id: UUID):
        if self.staff_user_repository is None:
            return None
        return await self.staff_user_repository.find_active_by_user_id(user_id)

    async def _validate_refresh_token(self):
        if not self.refresh_token:
            raise InvalidRefreshTokenError

    async def _get_user(self, user_id: UUID) -> User:
        result = await self.query_bus.ask(
            query=GetUserByIdQuery(user_id),
        )
        if not isinstance(result, User):
            raise UserNotFoundError
        return result
