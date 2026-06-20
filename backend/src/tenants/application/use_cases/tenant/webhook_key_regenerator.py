import secrets
from dataclasses import dataclass
from uuid import UUID

from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.interfaces.use_case import UseCase
from src.tenants.application.use_cases.tenant.mixins import TenantMixin
from src.tenants.domain.repositories.tenant import TenantRepository


@dataclass
class WebhookKeyRegenerator(TenantMixin, UseCase):
    tenant_id: UUID
    tenant_repository: TenantRepository

    async def execute(self) -> Tenant:
        tenant = await self.get_tenant()
        tenant.webhook_signature_key = f"whsec_{secrets.token_urlsafe(32)}"
        return await self.tenant_repository.persist(instance=tenant)
