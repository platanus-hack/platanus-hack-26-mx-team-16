"""``UpdateAlertPrefs`` — ``PUT /me/alerts {emailEnabled, slackWebhookUrl}`` (12-api).

Upsert over ``notification_prefs`` (PK = user_id). ``slack_webhook_url`` is
optional/nullable.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.sites.domain.models.notification_prefs import NotificationPrefs
from src.sites.domain.repositories.notification_prefs import NotificationPrefsRepository


@dataclass
class UpdateAlertPrefs(UseCase):
    user_id: UUID
    notification_prefs_repository: NotificationPrefsRepository
    email_enabled: bool | None = None
    slack_webhook_url: str | None = None

    async def execute(self, *args, **kwargs) -> NotificationPrefs:
        return await self.notification_prefs_repository.upsert(
            self.user_id,
            email_enabled=self.email_enabled,
            slack_webhook_url=self.slack_webhook_url,
        )
