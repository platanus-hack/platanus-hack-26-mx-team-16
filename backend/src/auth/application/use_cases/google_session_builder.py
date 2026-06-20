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
from src.staff.domain.repositories.staff_user import StaffUserRepository


@dataclass
class GoogleSessionBuilder(UseCase):
    google_tokens: GoogleAuthTokens
    google_user: GoogleUser | None
    query_bus: QueryBus
    token_service: TokenService
    # ADR 0001: emisión condicional del claim `is_staff` (fila staff activa).
    staff_user_repository: StaffUserRepository | None = None

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

        staff_user = await self._find_staff_user(user.uuid)
        jwt_session = await self.token_service.generate_token(
            sub=str(user.uuid),
            namespace="USER",
            extra_claims={"is_staff": True} if staff_user is not None else None,
        )
        tenant = await self._get_tenant(user_id=user.uuid)

        return TenantUserSession(
            session=jwt_session,
            user=user,
            tenant=tenant,
            # E5: el payload de sesión expone la identidad staff al FE.
            is_staff=staff_user is not None,
            staff_role=staff_user.role.value if staff_user is not None else None,
        )

    async def _get_tenant(self, user_id: UUID) -> Tenant | None:
        return await self.query_bus.ask(
            query=GetUserTenantQuery(user_id),
        )

    async def _find_staff_user(self, user_id: UUID):
        if self.staff_user_repository is None:
            return None
        return await self.staff_user_repository.find_active_by_user_id(user_id)
