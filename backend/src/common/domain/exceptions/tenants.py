from src.common.domain.constants import status
from src.common.domain.exceptions._base import DomainError


class TenantNotFoundError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="tenants.TenantNotFound",
            message="Tenant not found",
            status_code=status.HTTP_404_NOT_FOUND,
            context=context,
        )


class TenantLimitExcedeedError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="tenants.TenantLimitExcedeed",
            message="Tenants Limit Exceeded",
            status_code=status.HTTP_403_FORBIDDEN,
            context=context,
        )


class TenantRoleAlreadyExistsError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="tenants.TenantRoleAlreadyExists",
            message="Tenant Role alreade exists",
            status_code=status.HTTP_409_CONFLICT,
            context=context,
        )


class TenantRoleNotFoundError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="tenants.TenantRoleNotFound",
            message="Tenant Role not found",
            status_code=status.HTTP_409_CONFLICT,
            context=context,
        )


class InvitationNotFoundError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="tenants.InvitationNotFound",
            message="Invitation not found",
            status_code=status.HTTP_404_NOT_FOUND,
            context=context,
        )


class InvitationAlreadyAcceptedError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="tenants.InvitationAlreadyAccepted",
            message="Invitation has already been accepted",
            status_code=status.HTTP_410_GONE,
            context=context,
        )


class InvitationExpiredError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="tenants.InvitationExpired",
            message="Invitation has expired",
            status_code=status.HTTP_410_GONE,
            context=context,
        )


class InvitationPasswordRequiredError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="tenants.InvitationPasswordRequired",
            message="A password is required to accept this invitation",
            status_code=status.HTTP_400_BAD_REQUEST,
            context=context,
        )
