from fastapi import Depends

from src.common.domain.constants import status
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.entities.common.task_result import TaskResult
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.responses.api_json import ApiJSONResponse


class UserLogoutRequest(CamelCaseRequest):
    refresh_token: str


async def logout(
    payload: UserLogoutRequest,
    app_context: AppContext = Depends(get_app_context),
):
    token_service = app_context.domain.token_service
    await token_service.expire_refresh_token(payload.refresh_token)

    return ApiJSONResponse(content=TaskResult.success(), status_code=status.HTTP_200_OK)
