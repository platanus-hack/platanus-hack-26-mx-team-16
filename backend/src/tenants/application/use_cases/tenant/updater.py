from dataclasses import dataclass, field, replace
from typing import Any
from uuid import UUID

from src.assets.domain.services.storage import StorageService
from src.assets.infrastructure.helpers.storage_url import build_storage_url
from src.common.domain.entities.common.in_memory_file import InMemoryFile
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.helpers.models import override_dict_properties
from src.common.domain.interfaces.use_case import UseCase
from src.tenants.application.use_cases.tenant.mixins import TenantMixin
from src.tenants.domain.repositories.tenant import TenantRepository


@dataclass
class TenantUpdater(TenantMixin, UseCase):
    tenant_id: UUID
    tenant_repository: TenantRepository
    payload: dict[str, Any] = field(default_factory=dict)
    storage_service: StorageService | None = None
    logo: InMemoryFile | None = None

    async def execute(self) -> Tenant:
        tenant = await self.get_tenant()
        override_dict_properties(tenant, self.payload)
        await self._update_tenant_logo(tenant)
        return await self.tenant_repository.persist(instance=tenant)

    async def _update_tenant_logo(self, tenant: Tenant) -> None:
        if self.logo is None or not self.logo.has_content:
            return

        uploaded_file = self.storage_service.upload_file(
            replace(self.logo, file_path=self._build_logo_path(tenant, self.logo.file_name))
        )

        tenant.logo_url = build_storage_url(uploaded_file.file_path)

    def _build_logo_path(self, tenant: Tenant, file_name: str) -> str:
        tenant_slug = tenant.slug or str(tenant.uuid)
        return f"tenants/{tenant_slug}/logos/{file_name}"
