from dataclasses import dataclass

from src.common.application.commands.tenants import AssignTenantRoleInBatchCommand
from src.common.domain.buses.commands import CommandHandler
from src.tenants.application.use_cases.role.assigner import TenantRoleBatchAssigner
from src.tenants.domain.repositories.tenant import TenantRepository
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository
from src.tenants.domain.repositories.tenant_user import TenantUserRepository


@dataclass
class AssignTenantRolenBatchHandler(CommandHandler[AssignTenantRoleInBatchCommand]):
    tenant_user_repository: TenantUserRepository
    tenant_repository: TenantRepository
    role_repository: TenantRoleRepository

    async def execute(self, command: AssignTenantRoleInBatchCommand):
        return await TenantRoleBatchAssigner(
            tenant_id=command.tenant_id,
            role_repository=self.role_repository,
            tenant_user_repository=self.tenant_user_repository,
            tenant_repository=self.tenant_repository,
            role_slug="admin",
        ).execute()
