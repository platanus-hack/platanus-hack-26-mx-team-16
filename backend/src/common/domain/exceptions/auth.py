from src.common.domain.constants import status
from src.common.domain.exceptions import DomainError


class InvalidCredentialsError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="auth.InvalidCredentials",
            message="Credenciales Invalidas",
            status_code=status.HTTP_401_UNAUTHORIZED,
            context=context,
        )


class InvalidGoogleIdTokenError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="auth.InvalidGoogleIdoken",
            message="Invalid Google Id Token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            context=context,
        )


class RetrieveGoogleUserError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="auth.RetrieveGoogleUser",
            message="Retrieve Google User",
            status_code=status.HTTP_401_UNAUTHORIZED,
            context=context,
        )
