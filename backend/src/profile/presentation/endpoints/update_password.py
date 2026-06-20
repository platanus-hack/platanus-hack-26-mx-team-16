from fastapi import Depends

from src.common.application.commands.users import UpdateUserPasswordCommand
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.entities.common.task_result import TaskResult
from src.common.domain.models.user import User
from src.common.domain.helpers.models import override_model_properties
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.dependencies.session import get_authenticated_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse


class UpdatePasswordRequest(CamelCaseRequest):
    current_password: str
    new_password: str


async def update_password(
    payload: UpdatePasswordRequest,
    current_user: User = Depends(get_authenticated_user),
    app_context: AppContext = Depends(get_app_context),
    _response_model=TaskResult,
) -> ApiJSONResponse:
    override_model_properties(current_user, payload)

    await app_context.bus.command_bus.dispatch(
        command=UpdateUserPasswordCommand(
            user_id=current_user.uuid,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    )

    return ApiJSONResponse(
        content=TaskResult.success().model_dump(),
    )
