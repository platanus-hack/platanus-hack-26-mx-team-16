from dataclasses import dataclass

from src.common.application.queries.tenants import RemoveTenantPosesByIdQuery
from src.common.domain.buses.queries import QueryHandler
from src.tenants.domain.repositories.tenant_pos import TenantPOSRepository


@dataclass
class RemoveTenantPosesByIdHandler(QueryHandler[RemoveTenantPosesByIdQuery, None]):
    repository: TenantPOSRepository

    async def execute(self, query: RemoveTenantPosesByIdQuery) -> None:
        return await self.repository.batch_remove(instance_ids=query.tenant_pos_ids)
