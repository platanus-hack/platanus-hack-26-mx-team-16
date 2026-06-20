from src.common.domain.constants import status
from src.common.domain.exceptions import DomainError


class InvalidRefreshTokenError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="auth.InvalidRefreshToken",
            message="Invalid Refresh Token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            context=context,
        )
