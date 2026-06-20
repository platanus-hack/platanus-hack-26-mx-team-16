from dataclasses import dataclass
from uuid import UUID

from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.exceptions.tenants import TenantNotFoundError
from src.tenants.domain.repositories.tenant import TenantRepository


@dataclass
class TenantMixin:
    tenant_id: UUID
    tenant_repository: TenantRepository

    async def get_tenant(self) -> Tenant:
        tenant = await self.tenant_repository.find(tenant_id=self.tenant_id)
        if not tenant:
            raise TenantNotFoundError
        return tenant
