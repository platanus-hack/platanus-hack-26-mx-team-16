from uuid import UUID

from src.common.application.queries.tenants import GetTenantUserQuery, GetUserTenantQuery
from src.common.domain.buses.queries import QueryBus
from src.common.domain.entities.auth.user_session import TenantSessionParams
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.models.user import User
from src.common.domain.enums.users import TenantUserStatus


class TenantSessionMixin:
    query_bus: QueryBus

    async def _get_tenant_session_params(self, user: User) -> TenantSessionParams:
        tenant = await self._get_tenant(user_id=user.uuid)

        tenant_user = await self._get_tenant_user(user=user, tenant=tenant)
        tenant_role = tenant_user.tenant_role_meta if tenant_user else None
        render_tenant = tenant if tenant_user else None

        return TenantSessionParams(
            tenant=render_tenant,
            tenant_user=tenant_user,
            tenant_role=tenant_role,
        )

    async def _get_tenant(self, user_id: UUID) -> Tenant | None:
        tenant: Tenant | None = await self.query_bus.ask(
            query=GetUserTenantQuery(user_id),
        )  # type: ignore
        return tenant

    async def _get_tenant_user(
        self,
        user: User,
        tenant: Tenant | None = None,
    ) -> TenantUser | None:
        if not tenant:
            return None
        return await self.query_bus.ask(
            query=GetTenantUserQuery(
                user_id=user.uuid,
                tenant_id=tenant.uuid,
                status=TenantUserStatus.ACTIVE,
            ),
        )  # type: ignore
