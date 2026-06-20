from pydantic import Field, field_validator

from src.common.application.helpers.webhooks.url_validation import (
    InvalidWebhookUrlError,
    validate_webhook_url,
)
from src.common.domain.entities.common.requests import CamelCaseRequest


def _validate_url(url: str | None) -> str | None:
    if url is None:
        return None
    try:
        return validate_webhook_url(url)
    except InvalidWebhookUrlError as exc:
        raise ValueError(str(exc)) from exc


class CreateWebhookDestinationRequest(CamelCaseRequest):
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1, max_length=2048)
    description: str | None = Field(default=None, max_length=2000)
    enabled: bool = Field(default=True)
    subscribed_events: list[str] = Field(
        default_factory=lambda: ["document.extracted", "document.failed"]
    )
    secret: str | None = Field(default=None, max_length=512)
    api_version: str | None = Field(default=None, max_length=50)

    @field_validator("url")
    @classmethod
    def _check_url(cls, value: str) -> str:
        return _validate_url(value)  # type: ignore[return-value]


class UpdateWebhookDestinationRequest(CamelCaseRequest):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    description: str | None = Field(default=None, max_length=2000)
    enabled: bool | None = Field(default=None)
    subscribed_events: list[str] | None = Field(default=None)
    secret: str | None = Field(default=None, max_length=512)
    api_version: str | None = Field(default=None, max_length=50)

    @field_validator("url")
    @classmethod
    def _check_url(cls, value: str | None) -> str | None:
        return _validate_url(value)
