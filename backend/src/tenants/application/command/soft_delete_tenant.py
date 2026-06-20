from dataclasses import dataclass

from src.common.application.commands.tenants import SoftDeleteTenantCommand
from src.common.domain.buses.commands import CommandHandler
from src.tenants.application.use_cases.tenant.soft_deleter import TenantSoftDeleter
from src.tenants.domain.repositories.tenant import TenantRepository
from src.users.domain.repositories.user import UserRepository


@dataclass
class SoftDeleteTenantHandler(CommandHandler[SoftDeleteTenantCommand]):
    tenant_repository: TenantRepository
    user_repository: UserRepository

    async def execute(self, command: SoftDeleteTenantCommand) -> None:
        await TenantSoftDeleter(
            tenant_id=command.tenant_id,
            tenant_repository=self.tenant_repository,
            user_repository=self.user_repository,
        ).execute()
