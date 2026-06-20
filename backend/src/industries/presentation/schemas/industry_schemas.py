from pydantic import Field

from src.common.domain.entities.common.requests import CamelCaseRequest


class CreateIndustryRequest(CamelCaseRequest):
    slug: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    icon: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None)


class UpdateIndustryRequest(CamelCaseRequest):
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    icon: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None)
