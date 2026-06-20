from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.countries import CountryIsoCode
from src.common.domain.enums.currencies import CurrencyCode
from src.common.domain.enums.locales import TimeZone
from src.common.domain.enums.tenants import TenantStatus


class Tenant(BaseModel):
    uuid: UUID
    owner_id: UUID | None = Field(default=None)
    name: str = Field(..., min_length=1, max_length=150)
    slug: str = Field(..., min_length=1, max_length=50)
    time_zone: TimeZone = Field(default=None)
    country_code: CountryIsoCode = Field(default=None)
    currency_code: CurrencyCode = Field(default=None)
    logo_url: str | None = Field(default=None)
    status: TenantStatus = Field(default=TenantStatus.ACTIVE)
    is_deleted: bool = Field(default=False)
    webhook_signature_key: str | None = Field(default=None)
    plan_slug: str = Field(default="starter")
    monthly_page_quota_override: int | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    @property
    def is_active(self) -> bool:
        return self.status == TenantStatus.ACTIVE

    @property
    def persist_dict(self) -> dict[str, Any]:
        return {
            "owner_id": self.owner_id,
            "name": self.name,
            "slug": self.slug,
            "time_zone": str(self.time_zone),
            "country_code": str(self.country_code),
            "currency_code": str(self.currency_code),
            "logo_url": self.logo_url,
            "status": str(self.status),
            "is_deleted": self.is_deleted,
            "webhook_signature_key": self.webhook_signature_key,
        }
