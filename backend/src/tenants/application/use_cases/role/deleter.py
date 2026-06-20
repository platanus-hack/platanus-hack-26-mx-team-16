from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.tenants.application.use_cases.role.mixins import TenantRoleMixin
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository


@dataclass
class TenantRoleDeleter(TenantRoleMixin, UseCase):
    tenant_role_id: UUID
    role_repository: TenantRoleRepository

    async def execute(self) -> None:
        tenant_role = await self.get_tenant_role()
        await self.role_repository.delete(tenant_role.uuid)
