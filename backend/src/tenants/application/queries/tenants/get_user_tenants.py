from dataclasses import dataclass

from src.common.application.queries.tenants import GetUserTenantsQuery
from src.common.domain.buses.queries import QueryHandler
from src.common.domain.models.tenants.tenant import Tenant
from src.tenants.domain.repositories.tenant import TenantRepository


@dataclass
class GetUserTenantsHandler(QueryHandler[GetUserTenantsQuery, list[Tenant]]):
    repository: TenantRepository

    async def execute(self, query: GetUserTenantsQuery) -> list[Tenant]:
        return await self.repository.filter_by_user(user_id=query.user_id)
