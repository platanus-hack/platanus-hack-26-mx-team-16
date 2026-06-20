from uuid import UUID

from pydantic import Field

from src.common.domain.entities.common.requests import CamelCaseRequest


class SearchKBRequest(CamelCaseRequest):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    document_ids: list[UUID] | None = Field(default=None)


class SuggestRulesRequest(CamelCaseRequest):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=20)
    document_ids: list[UUID] | None = Field(default=None)
