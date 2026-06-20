from dataclasses import dataclass

from src.common.application.queries.tenants import RemoveTenantRolesByTenantIdQuery
from src.common.domain.buses.queries import QueryHandler
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository


@dataclass
class RemoveTenantRolesByTenantIdHandler(QueryHandler[RemoveTenantRolesByTenantIdQuery, None]):
    repository: TenantRoleRepository

    async def execute(self, query: RemoveTenantRolesByTenantIdQuery) -> None:
        return await self.repository.remove_by_tenant_id(tenant_id=query.tenant_id)
