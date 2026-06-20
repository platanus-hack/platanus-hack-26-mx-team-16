from fastapi import Depends, status

from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.session import get_authenticated_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse


async def get_profile(
    current_user: User = Depends(get_authenticated_user),
) -> ApiJSONResponse:
    return ApiJSONResponse(
        content=current_user.model_dump(),
        status_code=status.HTTP_200_OK,
    )
