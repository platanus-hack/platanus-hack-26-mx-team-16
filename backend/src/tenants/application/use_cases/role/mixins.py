from dataclasses import dataclass
from uuid import UUID

from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.exceptions.roles import TenantRoleNotFoundError
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository


@dataclass
class TenantRoleMixin:
    tenant_role_id: UUID
    role_repository: TenantRoleRepository

    async def get_tenant_role(self) -> TenantRole:
        instance = await self.role_repository.find(
            instance_id=self.tenant_role_id,
        )
        if not instance:
            raise TenantRoleNotFoundError
        return instance
