from uuid import UUID

from fastapi import Depends

from src.common.application.commands.users import SetUserCurrentTenantCommand
from src.common.domain.contexts.bus import BusContext
from src.common.domain.entities.common.task_result import TaskResult
from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import get_bus_context
from src.common.infrastructure.dependencies.session import get_authenticated_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse


async def update_me_tenant(
    tenant_id: UUID,
    bus: BusContext = Depends(get_bus_context),
    current_user: User = Depends(get_authenticated_user),
):
    await bus.command_bus.dispatch(
        command=SetUserCurrentTenantCommand(
            user_id=current_user.uuid,
            tenant_id=tenant_id,
        ),
    )

    return ApiJSONResponse(content=TaskResult.success())
