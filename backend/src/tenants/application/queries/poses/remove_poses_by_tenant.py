from dataclasses import dataclass

from src.common.application.queries.tenants import RemoveTenantPosesByTenantIdQuery
from src.common.domain.buses.queries import QueryHandler
from src.tenants.domain.repositories.tenant_pos import TenantPOSRepository


@dataclass
class RemoveTenantPosesByTenantIdHandler(QueryHandler[RemoveTenantPosesByTenantIdQuery, None]):
    repository: TenantPOSRepository

    async def execute(self, query: RemoveTenantPosesByTenantIdQuery) -> None:
        return await self.repository.remove_by_tenant_id(tenant_id=query.tenant_id)
