from src.common.domain.constants import status
from src.common.domain.exceptions import DomainError


class InsufficientPermissionsError(DomainError):
    def __init__(self, permissions: list[str], context=None):
        raw_permissions = ",".join(permissions)
        super().__init__(
            code="common.InsufficientPermissions",
            message=f"Required permissions: {raw_permissions}",
            status_code=status.HTTP_403_FORBIDDEN,
            context=context or {"required_permission": raw_permissions},
        )
