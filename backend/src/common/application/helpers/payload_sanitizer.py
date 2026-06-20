from typing import Any

from src.common.domain.enums.users import TenantUserStatus


def sanitize_permissions(permissions_value: Any) -> list[str]:
    """
    Normalizes a value into a list of strings for permissions.
    """
    if isinstance(permissions_value, (list, tuple, set)):
        return [str(item) for item in permissions_value]
    if permissions_value is None:
        return []
    return [str(permissions_value)]


def sanitize_role_update_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Sanitizes the payload for updating a TenantRole."""
    sanitized = {key: value for key, value in payload.items() if value is not None}

    if "permissions" in sanitized:
        permissions = sanitized["permissions"]
        if isinstance(permissions, (list, tuple, set)):
            sanitized["permissions"] = [str(permission) for permission in permissions]
        else:
            sanitized["permissions"] = [str(permissions)]

    return sanitized


def _normalize_status(value: Any) -> TenantUserStatus | None:
    """Normalizes a status value into a TenantUserStatus enum."""
    if isinstance(value, TenantUserStatus):
        return value
    if isinstance(value, str):
        return TenantUserStatus.from_value(value)
    return None
