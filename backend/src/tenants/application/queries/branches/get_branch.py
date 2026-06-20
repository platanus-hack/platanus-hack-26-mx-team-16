from dataclasses import dataclass

from src.common.application.queries.tenants import GetTenantBranchByIdQuery
from src.common.domain.buses.queries import QueryHandler
from src.common.domain.models.tenants.tenant import Tenant
from src.tenants.domain.repositories.tenant_branch import TenantBranchRepository


@dataclass
class GetTenantBranchByIdHandler(QueryHandler[GetTenantBranchByIdQuery, Tenant | None]):
    repository: TenantBranchRepository

    async def execute(self, query: GetTenantBranchByIdQuery) -> Tenant | None:
        return await self.repository.find(instance_id=query.tenant_branch_id)
