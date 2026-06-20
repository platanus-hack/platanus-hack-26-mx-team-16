from dataclasses import dataclass

from src.common.application.queries.tenants import RemoveTenantBranchesByTenantIdQuery
from src.common.domain.buses.queries import QueryHandler
from src.tenants.domain.repositories.tenant_branch import TenantBranchRepository


@dataclass
class RemoveTenantBranchesByTenantIdHandler(QueryHandler[RemoveTenantBranchesByTenantIdQuery, None]):
    repository: TenantBranchRepository

    async def execute(self, query: RemoveTenantBranchesByTenantIdQuery) -> None:
        return await self.repository.remove_by_tenant_id(tenant_id=query.tenant_id)
