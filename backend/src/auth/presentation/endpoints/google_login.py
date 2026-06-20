from fastapi import Depends, status

from src.auth.application.use_cases.google_session_builder import GoogleSessionBuilder
from src.auth.presentation.endpoints.helpers.google import get_google_tokens, verity_google_id_token
from src.auth.presentation.presenters.session import TenantUserSessionPresenter
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.responses.api_json import ApiJSONResponse


class GoogleLoginRequest(CamelCaseRequest):
    code: str


async def google_login(
    payload: GoogleLoginRequest,
    app_context: AppContext = Depends(get_app_context),
):
    google_tokens = await get_google_tokens(payload.code)
    google_user = await verity_google_id_token(google_tokens.id_token)

    user_session = await GoogleSessionBuilder(
        google_tokens=google_tokens,
        google_user=google_user,
        query_bus=app_context.bus.query_bus,
        token_service=app_context.domain.token_service,
        # ADR 0001: claim `is_staff` solo si hay fila staff activa.
        staff_user_repository=app_context.domain.staff_user_repository,
    ).execute()

    return ApiJSONResponse(
        content=TenantUserSessionPresenter(user_session).to_dict,
        status_code=status.HTTP_201_CREATED,
    )
