from src.common.domain.constants import status
from src.common.domain.exceptions import DomainError


class InvalidUserAuthError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="users.InvalidUserAuth",
            message="User requires email or phone",
            status_code=status.HTTP_400_BAD_REQUEST,
            context=context,
        )


class UserAlreadyExistError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="users.UserAlreadyExist",
            message="User already Exists",
            status_code=status.HTTP_400_BAD_REQUEST,
            context=context,
        )


class PaymentProductNotFoundError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="payments.PaymentProductNotFoundError",
            message="Payment Product Not Found",
            status_code=status.HTTP_400_BAD_REQUEST,
            context=context,
        )
