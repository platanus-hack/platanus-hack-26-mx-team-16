from pydantic import Field

from src.common.domain.entities.common.requests import CamelCaseRequest


class GoogleLoginRequest(CamelCaseRequest):
    access_token: str = Field(..., description="Google OAuth access token")
