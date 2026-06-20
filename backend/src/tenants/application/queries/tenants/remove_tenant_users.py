from dataclasses import dataclass

from src.common.application.queries.tenants import RemoveTenantUsersByTenantIdQuery
from src.common.domain.buses.queries import QueryHandler
from src.tenants.domain.repositories.tenant_user import TenantUserRepository


@dataclass
class RemoveTenantUsersByTenantIdHandler(QueryHandler[RemoveTenantUsersByTenantIdQuery, None]):
    repository: TenantUserRepository

    async def execute(self, query: RemoveTenantUsersByTenantIdQuery) -> None:
        return await self.repository.remove_tenant_users(tenant_id=query.tenant_id)
