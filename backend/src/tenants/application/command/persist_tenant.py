from dataclasses import dataclass

from src.common.application.commands.tenants import PersistTenantCommand
from src.common.domain.buses.commands import CommandHandler
from src.tenants.domain.repositories.tenant import TenantRepository


@dataclass
class PersistTenantHandler(CommandHandler[PersistTenantCommand]):
    repository: TenantRepository

    async def execute(self, command: PersistTenantCommand):
        return await self.repository.persist(instance=command.tenant)
