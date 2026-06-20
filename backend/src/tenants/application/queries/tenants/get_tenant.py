from dataclasses import dataclass

from src.common.application.queries.tenants import GetTenantByIdQuery
from src.common.domain.buses.queries import QueryHandler
from src.common.domain.models.tenants.tenant import Tenant
from src.tenants.domain.repositories.tenant import TenantRepository


@dataclass
class GetTenantByIdHandler(QueryHandler[GetTenantByIdQuery, Tenant | None]):
    repository: TenantRepository

    async def execute(self, query: GetTenantByIdQuery) -> Tenant | None:
        return await self.repository.find(tenant_id=query.tenant_id)
