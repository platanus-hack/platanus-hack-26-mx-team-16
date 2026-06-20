from dataclasses import dataclass

from src.common.application.queries.tenants import GetTenantRoleByIdQuery
from src.common.domain.buses.queries import QueryHandler
from src.common.domain.models.tenants.tenant_role import TenantRole
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository


@dataclass
class GetTenantRoleByIdHandler(QueryHandler[GetTenantRoleByIdQuery, TenantRole | None]):
    tenant_role_repository: TenantRoleRepository

    async def execute(self, query: GetTenantRoleByIdQuery) -> TenantRole | None:
        return await self.tenant_role_repository.find(query.tenant_role_id)
