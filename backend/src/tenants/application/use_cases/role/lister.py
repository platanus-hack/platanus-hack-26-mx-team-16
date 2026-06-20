from dataclasses import dataclass
from uuid import UUID

from src.common.domain.entities.common.collection import ListFilters
from src.common.domain.entities.common.pagination import Page
from src.common.domain.interfaces.use_case import UseCase
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository


@dataclass
class TenantRoleLister(UseCase):
    tenant_id: UUID
    filters: ListFilters
    role_repository: TenantRoleRepository

    async def execute(self, *args, **kwargs) -> Page:
        return await self.role_repository.filter_paginated(
            tenant_id=self.tenant_id,
            filters=self.filters,
        )
