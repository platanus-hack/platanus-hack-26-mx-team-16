from dataclasses import dataclass

from src.common.application.queries.tenants import RemoveTenantBranchesByIdQuery
from src.common.domain.buses.queries import QueryHandler
from src.tenants.domain.repositories.tenant_branch import TenantBranchRepository


@dataclass
class RemoveTenantBranchesByIdHandler(QueryHandler[RemoveTenantBranchesByIdQuery, None]):
    repository: TenantBranchRepository

    async def execute(self, query: RemoveTenantBranchesByIdQuery) -> None:
        return await self.repository.batch_remove(instance_ids=query.tenant_branch_ids)
