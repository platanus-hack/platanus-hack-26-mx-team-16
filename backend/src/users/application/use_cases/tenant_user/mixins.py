from uuid import UUID

from src.common.application.queries.tenants import GetTenantRoleByIdQuery
from src.common.application.queries.users import (
    GetTenantUserByIdQuery,
)
from src.common.domain.buses.queries import QueryBus
from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.exceptions.tenants import TenantRoleNotFoundError
from src.common.domain.exceptions.users import (
    TenantUserNotFoundError,
)


class TenantUserMixin:
    tenant_id: UUID
    tenant_user_id: UUID
    query_bus: QueryBus

    async def _get_tenant_user(self) -> TenantUser:
        tenant_user: TenantUser | None = await self.query_bus.ask(  # type: ignore
            query=GetTenantUserByIdQuery(tenant_user_id=self.tenant_user_id)
        )

        if not tenant_user or tenant_user.tenant_id != self.tenant_id:
            raise TenantUserNotFoundError

        return tenant_user


class TenantRoleValidatorMixin:
    query_bus: QueryBus

    async def _assert_tenant_role_exists(self, tenant_role_id: UUID) -> None:
        tenant_role = await self.query_bus.ask(query=GetTenantRoleByIdQuery(tenant_role_id=tenant_role_id))  # type: ignore
        if tenant_role is None:
            raise TenantRoleNotFoundError

    async def _get_tenant_role(self, tenant_role_id: UUID) -> TenantRole | None:
        return await self.query_bus.ask(
            query=GetTenantRoleByIdQuery(tenant_role_id=tenant_role_id),
        )
