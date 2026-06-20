from fastapi import Depends

from src.auth.application.use_cases.refresh_builder import TenantUserRefreshSessionBuilder
from src.auth.presentation.presenters.session import TenantUserSessionPresenter
from src.common.domain.constants import status
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.responses.api_json import ApiJSONResponse


class UserRefreshRequest(CamelCaseRequest):
    refresh_token: str


async def refresh(
    payload: UserRefreshRequest,
    app_context: AppContext = Depends(get_app_context),
):
    user_session = await TenantUserRefreshSessionBuilder(
        refresh_token=payload.refresh_token,
        query_bus=app_context.bus.query_bus,
        token_service=app_context.domain.token_service,
        # E5 · ADR 0001: re-expone is_staff/staff_role en el payload de sesión.
        staff_user_repository=app_context.domain.staff_user_repository,
    ).execute()

    return ApiJSONResponse(
        content=TenantUserSessionPresenter(user_session).to_dict,
        status_code=status.HTTP_200_OK,
    )
