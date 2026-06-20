from dataclasses import dataclass

from src.common.application.queries.poses import GetTenantPosByCodeQuery, GetTenantPosByIdQuery
from src.common.domain.buses.queries import QueryHandler
from src.common.domain.entities.tenants.tenant_pos import TenantPOS
from src.tenants.domain.repositories.tenant_pos import TenantPOSRepository


@dataclass
class GetTenantPosByCodeHandler(QueryHandler[GetTenantPosByCodeQuery, TenantPOS | None]):
    repository: TenantPOSRepository

    async def execute(self, query: GetTenantPosByCodeQuery) -> TenantPOS | None:
        return await self.repository.find_by_code(code=query.code)


@dataclass
class GetTenantPosByIdHandler(QueryHandler[GetTenantPosByIdQuery, TenantPOS | None]):
    repository: TenantPOSRepository

    async def execute(self, query: GetTenantPosByIdQuery) -> TenantPOS | None:
        return await self.repository.find(instance_id=query.instance_id)
