from dataclasses import dataclass

from src.common.application.queries.tenants import RemoveTenantByIdQuery
from src.common.domain.buses.queries import QueryHandler
from src.tenants.domain.repositories.tenant import TenantRepository


@dataclass
class RemoveTenantByIdHandler(QueryHandler[RemoveTenantByIdQuery, None]):
    repository: TenantRepository

    async def execute(self, query: RemoveTenantByIdQuery) -> None:
        return await self.repository.remove(tenant_id=query.tenant_id)
