from fastapi import status
from pydantic import BaseModel, EmailStr, Field

from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.users.application.use_cases.user.user_registerer import UserRegisterer


class RegisterUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    is_superuser: bool = False


async def register_user(
    request: RegisterUserRequest,
    domain_context: DomainContextDep,
) -> ApiJSONResponse:
    user = await UserRegisterer(
        user=User.from_raw(email=str(request.email)),
        password=request.password,
        user_repository=domain_context.user_repository,
        is_superuser=False,
    ).execute()

    return ApiJSONResponse(
        content=user.model_dump(),
        status_code=status.HTTP_201_CREATED,
    )
