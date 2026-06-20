from uuid import UUID

from fastapi import Depends

from src.common.application.commands.users import SetUserPasswordCommand
from src.common.domain.constants import status
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.entities.common.task_result import TaskResult
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.api_keys import get_admin_api_key
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.responses.api_json import ApiJSONResponse


class SetUserPasswordRequest(CamelCaseRequest):
    user_id: UUID
    password: str


async def set_user_password(
    request: SetUserPasswordRequest,
    app_context: AppContext = Depends(get_app_context),
    _api_key: str = Depends(get_admin_api_key),
) -> ApiJSONResponse:
    await app_context.bus.command_bus.dispatch(
        command=SetUserPasswordCommand(
            user_id=request.user_id,
            password=request.password,
        ),
    )
    return ApiJSONResponse(
        content=TaskResult.success().to_dict,
        status_code=status.HTTP_201_CREATED,
    )
