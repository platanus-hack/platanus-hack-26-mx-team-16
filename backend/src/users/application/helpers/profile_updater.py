from typing import Any

from src.common.domain.models.tenants.tenant_user import TenantUser
from src.users.domain.repositories.user import UserRepository


def _should_update_user_profile(payload: dict[str, Any]) -> bool:
    """Checks if the payload contains fields for updating the user profile."""
    return any(field in payload for field in ("first_name", "last_name"))


async def update_user_profile_from_payload(
    tenant_user: TenantUser,
    sanitized_payload: dict[str, Any],
    user_repository: UserRepository,
) -> None:
    """
    Updates a user's profile (first/last name) from a payload if needed.

    This function checks if the necessary data is present, updates the
    user object, persists it, and removes the keys from the payload dict.

    Args:
        tenant_user: The TenantUser entity containing the user to update.
        sanitized_payload: The dictionary of sanitized data. This dictionary
                           will be mutated (first/last name keys will be popped).
        user_repository: The repository to persist user changes.
    """
    if not (tenant_user.user and _should_update_user_profile(sanitized_payload)):
        return

    if "first_name" in sanitized_payload:
        tenant_user.user.first_name = sanitized_payload.pop("first_name")
    if "last_name" in sanitized_payload:
        tenant_user.user.last_name = sanitized_payload.pop("last_name")

    tenant_user.user = await user_repository.persist(instance=tenant_user.user)
