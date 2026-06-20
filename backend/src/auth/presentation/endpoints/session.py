from fastapi import Depends

from src.auth.application.use_cases.session_builder import TenantUserProfileBuilder
from src.auth.presentation.presenters.session import TenantUserProfilePresenter
from src.common.domain.constants import status
from src.common.domain.entities.auth.user_session import TenantUserSession
from src.common.domain.models.user import User
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.dependencies.session import get_authenticated_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse


async def session(
    app_context: AppContext = Depends(get_app_context),
    current_user: User = Depends(get_authenticated_user),
    response_model=TenantUserSession,  # noqa
):
    tenant_user_profile = await TenantUserProfileBuilder(
        user=current_user,
        query_bus=app_context.bus.query_bus,
    ).execute()

    return ApiJSONResponse(
        content=TenantUserProfilePresenter(instance=tenant_user_profile).to_dict,
        status_code=status.HTTP_200_OK,
    )
