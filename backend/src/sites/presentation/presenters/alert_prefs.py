"""Alert-prefs presenter — ``NotificationPrefs`` → camelCase (12-api §"Alertas")."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.common.domain.interfaces.presenter import Presenter
from src.sites.domain.models.notification_prefs import NotificationPrefs


@dataclass
class AlertPrefsPresenter(Presenter[NotificationPrefs]):
    instance: NotificationPrefs

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "emailEnabled": self.instance.email_enabled,
            "slackWebhookUrl": self.instance.slack_webhook_url,
        }
