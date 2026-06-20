from dataclasses import dataclass

from src.common.application.commands.users import DeleteTenantUserCommand
from src.common.domain.buses.commands import CommandHandler
from src.tenants.domain.repositories.tenant_user import TenantUserRepository


@dataclass
class DeleteTenantUserHandler(CommandHandler[DeleteTenantUserCommand]):
    tenant_user_repository: TenantUserRepository

    async def execute(self, command: DeleteTenantUserCommand):
        await self.tenant_user_repository.remove(
            tenant_user_id=command.tenant_user_id,
        )
