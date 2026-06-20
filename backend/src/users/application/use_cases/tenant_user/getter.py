from dataclasses import dataclass
from uuid import UUID

from src.common.domain.buses.queries import QueryBus
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.interfaces.use_case import UseCase
from src.users.application.use_cases.tenant_user.mixins import TenantUserMixin


@dataclass
class TenantUserGetter(TenantUserMixin, UseCase):
    tenant_id: UUID
    tenant_user_id: UUID
    query_bus: QueryBus

    async def execute(self) -> TenantUser:
        return await self._get_tenant_user()
