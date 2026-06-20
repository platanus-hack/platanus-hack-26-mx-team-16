from typing import Any
from uuid import UUID

from pydantic import Field

from src.common.domain.entities.common.collection import ListFilters
from src.common.domain.enums.users import TenantUserStatus


class TenantUserFilters(ListFilters):
    search: str | None = Field(default=None)
    statuses: str | None = Field(default=None)

    tenant_ids: list[UUID] | None = Field(default=None, alias="tenantIds")
    exclude_ids: list[UUID] | None = Field(default=None, alias="excludeIds")

    def model_post_init(self, context: Any, /) -> None:
        self.tenant_ids = self.tenant_ids or []
        self.exclude_ids = self.exclude_ids or []

    @property
    def enum_statuses(self) -> list[TenantUserStatus]:
        return self.parse_enum_values(self.statuses, TenantUserStatus)
