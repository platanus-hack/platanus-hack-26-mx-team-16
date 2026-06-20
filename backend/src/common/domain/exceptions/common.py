from pydantic import BaseModel, Field

from src.common.domain.constants import status
from src.common.domain.exceptions import DomainError


class ErrorItem(BaseModel):
    code: str = Field(..., description="Error code (e.g., 'auth.InvalidCredentials')")
    message: str = Field(..., description="Human-readable error message")


class ValidationFeedback(BaseModel):
    code: str = Field(..., description="Validation error code")
    message: str = Field(..., description="Validation error message")


class ErrorFeedback(BaseModel):
    errors: list[ErrorItem] = Field(..., description="List of errors")
    validation: dict[str, ValidationFeedback] | None = Field(None, description="Field-specific validation errors")


class InvalidPaginationCursorError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="common.InvalidPaginationCursor",
            message="Invalid pagination cursor",
            status_code=status.HTTP_400_BAD_REQUEST,
            context=context,
        )


class InvalidOrExpiredTokenError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="common.InvalidOrExpiredToken",
            message="Invalid or expired token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            context=context,
        )


class InvalidOrExpiredRefreshTokenError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="common.InvalidRefreshToken",
            message="Invalid Refresh Token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            context=context,
        )


class InvalidAdminApiKeyError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="common.InvalidAdminApiKey",
            message="Invalid admin api key",
            status_code=status.HTTP_401_UNAUTHORIZED,
            context=context,
        )
