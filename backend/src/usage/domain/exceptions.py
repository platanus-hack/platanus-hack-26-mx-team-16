from src.common.domain.constants import status
from src.common.domain.exceptions._base import DomainError


class QuotaExceededError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="usage.QuotaExceeded",
            message="Monthly page quota has been reached. Upgrade your plan to continue processing.",
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            context=context,
        )


class QuotaNearLimitError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="usage.QuotaNearLimit",
            message="Usage has reached 80% of the monthly quota.",
            status_code=status.HTTP_200_OK,
            context=context,
        )
