from dataclasses import dataclass

from src.common.application.queries.tenants import GetTenantUserQuery
from src.common.domain.buses.queries import QueryHandler
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.tenants.domain.repositories.tenant_user import TenantUserRepository


@dataclass
class GetTenantUserHandler(QueryHandler[GetTenantUserQuery, TenantUser | None]):
    repository: TenantUserRepository

    async def execute(self, query: GetTenantUserQuery) -> TenantUser | None:
        return await self.repository.find_by_args(
            user_id=query.user_id,
            tenant_id=query.tenant_id,
            status=query.status,
        )
