from dataclasses import dataclass
from uuid import UUID

from src.common.application.commands.users import DeleteTenantUserCommand
from src.common.domain.buses.commands import CommandBus
from src.common.domain.buses.queries import QueryBus
from src.common.domain.interfaces.use_case import UseCase
from src.users.application.use_cases.tenant_user.mixins import TenantUserMixin


@dataclass
class TenantUserRemover(TenantUserMixin, UseCase):
    tenant_id: UUID
    tenant_user_id: UUID
    query_bus: QueryBus
    command_bus: CommandBus

    async def execute(self) -> None:
        await self._get_tenant_user()
        await self.command_bus.dispatch(
            command=DeleteTenantUserCommand(tenant_user_id=self.tenant_user_id),
        )
