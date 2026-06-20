from dataclasses import dataclass

from src.common.application.commands.users import SetupTenantUserCommand
from src.common.domain.buses.commands import CommandHandler
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.tenants.domain.repositories.tenant_user import TenantUserRepository


@dataclass
class SetupTenantUserHandler(CommandHandler):
    repository: TenantUserRepository

    async def execute(self, command: SetupTenantUserCommand):
        tenant_user = TenantUser(
            tenant_id=command.tenant_id,
            user_id=command.user_id,
            is_owner=command.is_owner,
            status=command.status,
            tenant_role_id=command.tenant_role_id,
            permissions=[str(permission) for permission in (command.permissions or [])],
        )

        return await self.repository.persist(
            instance=tenant_user,
        )
