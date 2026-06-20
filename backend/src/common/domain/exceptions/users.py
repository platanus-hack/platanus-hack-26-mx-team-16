from src.common.domain.constants import status
from src.common.domain.exceptions._base import DomainError


class UserNotFoundError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="users.UserNotFound",
            message="User not found",
            status_code=status.HTTP_404_NOT_FOUND,
            context=context,
        )


class TenantUserRequiredError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="users.TenantUserRequiredError",
            message="Tenant User Required",
            status_code=status.HTTP_403_FORBIDDEN,
            context=context,
        )


class TenantUserNotFoundError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="users.TenantUserNotFound",
            message="Tenant user not found",
            status_code=status.HTTP_404_NOT_FOUND,
            context=context,
        )


class UserEmailAlreadyExistsError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="users.UserEmailAddressAlreadyExists",
            message="User email address already exists",
            status_code=status.HTTP_400_BAD_REQUEST,
            context=context,
        )


class UserPhoneNumberAlreadyExistsError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="users.UserPhoneNumberAlreadyExists",
            message="User phone number already exists",
            status_code=status.HTTP_400_BAD_REQUEST,
            context=context,
        )
