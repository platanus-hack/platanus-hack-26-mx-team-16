from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.common.domain.entities.common.collection import ListFilters
from src.common.domain.enums.currencies import CurrencyCode


class TenantBalanceFilters(ListFilters):
    tenant_ids: list[UUID] | None = Field(default=None)
    date_from: datetime | None = Field(default=None)
    date_to: datetime | None = Field(default=None)
    currency_codes: str | None = Field(default=None)

    @property
    def enum_currency_codes(self) -> list[CurrencyCode]:
        return self.parse_enum_values(self.currency_codes, CurrencyCode)
