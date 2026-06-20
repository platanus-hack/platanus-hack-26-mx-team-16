import uuid
from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.tenants.application.use_cases.tenant.mixins import TenantMixin
from src.tenants.domain.repositories.tenant import TenantRepository
from src.users.domain.repositories.user import UserRepository


@dataclass
class TenantSoftDeleter(TenantMixin, UseCase):
    tenant_id: UUID
    tenant_repository: TenantRepository
    user_repository: UserRepository

    async def execute(self) -> None:
        tenant = await self.get_tenant()
        tenant.is_deleted = True
        tenant.slug = uuid.uuid4().hex
        await self.tenant_repository.persist(instance=tenant)
        await self.user_repository.clear_current_tenant_for_users(self.tenant_id)
