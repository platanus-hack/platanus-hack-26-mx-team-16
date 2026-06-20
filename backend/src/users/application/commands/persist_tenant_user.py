from dataclasses import dataclass

from src.common.application.commands.users import PersistTenantUserCommand
from src.common.domain.buses.commands import CommandHandler
from src.tenants.domain.repositories.tenant_user import TenantUserRepository


@dataclass
class PersistTenantUserHandler(CommandHandler[PersistTenantUserCommand]):
    tenant_user_repository: TenantUserRepository

    async def execute(self, command: PersistTenantUserCommand):
        await self.tenant_user_repository.persist(
            instance=command.tenant_user,
        )
