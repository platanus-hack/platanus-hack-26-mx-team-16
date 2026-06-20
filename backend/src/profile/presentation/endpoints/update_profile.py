from fastapi import Depends, status

from src.common.application.commands.users import PersistUserCommand
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.entities.email_address import RawEmailAddress
from src.common.domain.entities.phone_number import RawPhoneNumber
from src.common.domain.models.user import User
from src.common.domain.helpers.models import override_model_properties
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.dependencies.session import get_authenticated_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse


class UpdateProfileRequest(CamelCaseRequest):
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email_address: RawEmailAddress | None = None
    phone_number: RawPhoneNumber | None = None


async def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_authenticated_user),
    app_context: AppContext = Depends(get_app_context),
) -> ApiJSONResponse:
    override_model_properties(current_user, payload)

    await app_context.bus.command_bus.dispatch(command=PersistUserCommand(current_user))

    return ApiJSONResponse(
        content=current_user.model_dump(),
        status_code=status.HTTP_200_OK,
    )
