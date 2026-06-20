from dataclasses import dataclass
from uuid import UUID

from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.interfaces.use_case import UseCase
from src.tenants.application.use_cases.role.mixins import TenantRoleMixin
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository


@dataclass
class TenantRoleGetter(TenantRoleMixin, UseCase):
    tenant_role_id: UUID
    role_repository: TenantRoleRepository

    async def execute(self) -> TenantRole:
        return await self.get_tenant_role()
