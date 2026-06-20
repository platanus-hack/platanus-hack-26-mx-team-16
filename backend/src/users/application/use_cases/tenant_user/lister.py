from dataclasses import dataclass

from src.common.domain.entities.common.pagination import Page
from src.common.domain.filters.tenants.tenant_user import TenantUserFilters
from src.common.domain.interfaces.use_case import UseCase
from src.tenants.domain.repositories.tenant_user import TenantUserRepository


@dataclass
class TenantUserLister(UseCase):
    filters: TenantUserFilters
    user_repository: TenantUserRepository

    async def execute(self, *args, **kwargs) -> Page:
        return await self.user_repository.filter_paginated(
            filters=self.filters,
        )
