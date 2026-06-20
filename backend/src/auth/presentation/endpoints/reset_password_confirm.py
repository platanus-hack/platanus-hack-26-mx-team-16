from fastapi import Depends, status
from pydantic import Field

from src.auth.application.use_cases.reset_password_with_token import (
    ResetPasswordWithToken,
)
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.entities.common.task_result import TaskResult
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.responses.api_json import ApiJSONResponse


class ResetPasswordConfirmRequest(CamelCaseRequest):
    token: str = Field(min_length=1)
    password: str = Field(min_length=8, max_length=128)


async def reset_password_confirm(
    payload: ResetPasswordConfirmRequest,
    app_context: AppContext = Depends(get_app_context),
):
    await ResetPasswordWithToken(
        token=payload.token,
        new_password=payload.password,
        user_repository=app_context.domain.user_repository,
        token_service=app_context.domain.token_service,
    ).execute()

    return ApiJSONResponse(
        content=TaskResult.success(),
        status_code=status.HTTP_200_OK,
    )
