from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.webhook_destination import WebhookDestination


@dataclass
class WebhookDestinationPresenter(Presenter[WebhookDestination]):
    """Webhook-destination view. Never exposes the stored ``secret`` — only a
    ``has_secret`` flag (spec connections §9). ``status`` is derived from
    ``enabled`` for a Stripe-style ACTIVE/DISABLED badge."""

    instance: WebhookDestination

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "tenant_id": str(self.instance.tenant_id),
            "workflow_id": str(self.instance.workflow_id),
            "provider": self.instance.provider.value,
            "account_id": str(self.instance.account_id) if self.instance.account_id else None,
            "name": self.instance.name,
            "url": self.instance.url,
            "description": self.instance.description,
            "enabled": self.instance.enabled,
            "status": "ACTIVE" if self.instance.enabled else "DISABLED",
            "subscribed_events": list(self.instance.subscribed_events),
            "api_version": self.instance.api_version,
            "has_secret": self.instance.secret is not None,
            "created_at": optional_datetime_string(self.instance.created_at),
            "updated_at": optional_datetime_string(self.instance.updated_at),
        }

    @property
    def secret_dict(self) -> dict[str, Any]:
        """Returned once by the regenerate-secret endpoint so the UI can reveal it."""
        return {**self.to_dict, "secret": self.instance.secret}
