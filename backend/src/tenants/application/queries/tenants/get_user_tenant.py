from dataclasses import dataclass

from src.common.application.queries.tenants import GetUserTenantQuery
from src.common.domain.buses.queries import QueryHandler
from src.common.domain.models.tenants.tenant import Tenant
from src.tenants.domain.repositories.tenant import TenantRepository


@dataclass
class GetUserTenantHandler(QueryHandler[GetUserTenantQuery, list[Tenant]]):
    repository: TenantRepository

    async def execute(self, query: GetUserTenantQuery) -> Tenant | None:
        return await self.repository.find_by_user(
            user_id=query.user_id,
        )
