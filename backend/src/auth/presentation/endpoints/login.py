from fastapi import Depends, status

from src.auth.application.use_cases.session_builder import TenantUserSessionBuilder
from src.auth.presentation.presenters.session import TenantUserSessionPresenter
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.responses.api_json import ApiJSONResponse


class LoginRequest(CamelCaseRequest):
    email: str
    password: str


async def login(
    payload: LoginRequest,
    app_context: AppContext = Depends(get_app_context),
):
    tenant_user_session = await TenantUserSessionBuilder(
        email=payload.email,
        password=payload.password,
        query_bus=app_context.bus.query_bus,
        token_service=app_context.domain.token_service,
        # ADR 0001: claim `is_staff` solo si hay fila staff activa.
        staff_user_repository=app_context.domain.staff_user_repository,
    ).execute()

    return ApiJSONResponse(
        content=TenantUserSessionPresenter(tenant_user_session).to_dict,
        status_code=status.HTTP_201_CREATED,
    )
