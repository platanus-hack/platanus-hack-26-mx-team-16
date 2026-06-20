from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.helpers.models import override_dict_properties
from src.common.domain.interfaces.use_case import UseCase
from src.tenants.application.use_cases.role.mixins import TenantRoleMixin
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository


@dataclass
class TenantRoleUpdater(TenantRoleMixin, UseCase):
    tenant_role_id: UUID
    payload: dict[str, Any]
    role_repository: TenantRoleRepository

    async def execute(self) -> TenantRole:
        tenant_role = await self.get_tenant_role()
        override_dict_properties(tenant_role, self.payload)
        return await self.role_repository.persist(tenant_role)
