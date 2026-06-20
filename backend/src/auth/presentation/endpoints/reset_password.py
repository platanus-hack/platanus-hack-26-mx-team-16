from fastapi import Depends, status

from src.auth.application.use_cases.request_password_reset import (
    RequestPasswordReset,
)
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.entities.common.task_result import TaskResult
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.responses.api_json import ApiJSONResponse


class ResetPasswordRequest(CamelCaseRequest):
    email: str


async def reset_password(
    payload: ResetPasswordRequest,
    app_context: AppContext = Depends(get_app_context),
):
    await RequestPasswordReset(
        email=payload.email,
        user_repository=app_context.domain.user_repository,
        token_service=app_context.domain.token_service,
        command_bus=app_context.bus.command_bus,
    ).execute()

    # Always return 200 to avoid leaking whether the email is registered.
    return ApiJSONResponse(
        content=TaskResult.success(),
        status_code=status.HTTP_200_OK,
    )
