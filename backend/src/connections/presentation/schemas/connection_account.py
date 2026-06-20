from pydantic import Field

from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.enums.connections import (
    ConnectionCapability,
    ConnectionProvider,
    ConnectionStatus,
)


class CreateConnectionAccountRequest(CamelCaseRequest):
    provider: ConnectionProvider
    display_name: str = Field(..., min_length=1, max_length=255)
    capabilities: list[ConnectionCapability] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)
    secret: str | None = Field(default=None, max_length=512)


class UpdateConnectionAccountRequest(CamelCaseRequest):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    capabilities: list[ConnectionCapability] | None = Field(default=None)
    status: ConnectionStatus | None = Field(default=None)
    config: dict | None = Field(default=None)
    secret: str | None = Field(default=None, max_length=512)
