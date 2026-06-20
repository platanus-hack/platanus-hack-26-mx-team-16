"""Tenant M2M API-key errors (F9)."""

from src.common.domain.exceptions._base import DomainError


class InvalidTenantApiKeyError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="api_key.invalid",
            message="Missing or invalid tenant API key.",
            status_code=401,
        )
