from dataclasses import dataclass

from src.common.application.commands.tenants import BootstrapTenantRolesCommand
from src.common.domain.buses.commands import CommandHandler
from src.tenants.application.use_cases.role.bootstraper import TenantRolesBootstrapper
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository


@dataclass
class BootstrapTenantRolesHandler(CommandHandler[BootstrapTenantRolesCommand]):
    role_repository: TenantRoleRepository

    async def execute(self, command: BootstrapTenantRolesCommand):
        return await TenantRolesBootstrapper(
            tenant_id=command.tenant_id,
            role_repository=self.role_repository,
        ).execute()
