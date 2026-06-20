from uuid import UUID

from pydantic import BaseModel, Field

from src.common.domain.enums.countries import CountryIsoCode


class TenantMixin(BaseModel):
    tenant_id: UUID


class OptionalTenantBranchMixin(BaseModel):
    tenant_branch_id: UUID | None = Field(default=None)


class OptionalTenantMixin(BaseModel):
    tenant_id: UUID | None = None


class LocationMixin(BaseModel):
    address: str | None = Field(default=None)
    city: str | None = Field(default=None)
    state_province: str | None = Field(default=None)
    country: CountryIsoCode | None = Field(default=None)
