from typing import Any

from pydantic import BaseModel, Field


class GoogleLoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user_info: dict[str, Any] = Field(..., description="User information")


class GoogleUserInfo(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    google_id: str
