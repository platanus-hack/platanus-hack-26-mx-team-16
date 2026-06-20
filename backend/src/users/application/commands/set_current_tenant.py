from dataclasses import dataclass

from src.common.application.commands.users import SetUserCurrentTenantCommand
from src.common.application.logging import get_logger

logger = get_logger(__name__)
from src.common.application.queries.tenants import GetUserTenantsQuery
from src.common.domain.buses.commands import CommandHandler
from src.common.domain.buses.queries import QueryBus
from src.common.domain.models.tenants.tenant import Tenant
from src.users.domain.repositories.user import UserRepository


@dataclass
class SetUserCurrentTenantHandler(CommandHandler[SetUserCurrentTenantCommand]):
    user_repository: UserRepository
    query_bus: QueryBus

    async def execute(self, command: SetUserCurrentTenantCommand):
        result = await self.query_bus.ask(query=GetUserTenantsQuery(user_id=command.user_id))
        user_tenants: list[Tenant] | None = result if isinstance(result, list) else None
        user_tenants = user_tenants or []
        uer_tenant_ids = [tenant.uuid for tenant in user_tenants]

        if command.tenant_id not in uer_tenant_ids:
            logger.error(
                "user.current_tenant.forbidden",
                user_id=str(command.user_id),
                tenant_id=str(command.tenant_id),
            )
            return

        await self.user_repository.update_current_tenant(
            user_id=command.user_id,
            tenant_id=command.tenant_id,
        )
