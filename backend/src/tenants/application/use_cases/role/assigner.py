from dataclasses import dataclass
from uuid import UUID

from src.common.domain.exceptions.tenants import TenantNotFoundError, TenantRoleNotFoundError
from src.common.domain.filters.tenants.tenant_user import TenantUserFilters
from src.common.domain.interfaces.use_case import UseCase
from src.tenants.domain.repositories.tenant import TenantRepository
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository
from src.tenants.domain.repositories.tenant_user import TenantUserRepository


@dataclass
class TenantRoleBatchAssigner(UseCase):
    tenant_id: UUID
    role_slug: str
    tenant_user_repository: TenantUserRepository
    tenant_repository: TenantRepository
    role_repository: TenantRoleRepository

    async def execute(self):
        tenant = await self.tenant_repository.find(self.tenant_id)
        if not tenant:
            raise TenantNotFoundError

        tenant_role = await self.role_repository.find_by_slug(
            tenant_id=self.tenant_id,
            slug=self.role_slug,
        )
        if not tenant_role:
            raise TenantRoleNotFoundError

        tenant_users = await self.tenant_user_repository.filter(filters=TenantUserFilters(tenantIds=[tenant.uuid]))
        for tenant_user in tenant_users:
            if tenant_user.tenant_role_id:
                continue
            tenant_user.tenant_role = tenant_role
            tenant_user.tenant_role_id = tenant_role.uuid
            await self.tenant_user_repository.persist(tenant_user)
