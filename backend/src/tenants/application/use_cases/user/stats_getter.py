from dataclasses import dataclass
from uuid import UUID

from src.common.domain.entities.tenants.tenant_user_stats import TenantUserStats
from src.common.domain.enums.users import TenantUserStatus
from src.common.domain.interfaces.use_case import UseCase
from src.tenants.domain.repositories.tenant_user import TenantUserRepository


@dataclass
class TenantUserStatsGetter(UseCase):
    tenant_id: UUID
    tenant_user_repository: TenantUserRepository
    excluded_tenant_user_ids: list[UUID] = None

    async def execute(self, *args, **kwargs) -> TenantUserStats:
        counts_by_status = await self.tenant_user_repository.count_by_status(
            tenant_id=self.tenant_id,
            excluded_tenant_user_ids=self.excluded_tenant_user_ids or [],
        )

        return TenantUserStats(
            total=sum(counts_by_status.values()),
            active=counts_by_status.get(TenantUserStatus.ACTIVE, 0),
            pending=counts_by_status.get(TenantUserStatus.PENDING, 0),
            inactive=counts_by_status.get(TenantUserStatus.INACTIVE, 0),
        )
