"""``GetAlertPrefs`` — ``GET /me/alerts`` (12-api §"Alertas").

Account-level alert-channel prefs. Defaults to ``{email_enabled: True,
slack_webhook_url: None}`` when the user has no row yet (email to the active owner
is on by default).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.sites.domain.models.notification_prefs import NotificationPrefs
from src.sites.domain.repositories.notification_prefs import NotificationPrefsRepository


@dataclass
class GetAlertPrefs(UseCase):
    user_id: UUID
    notification_prefs_repository: NotificationPrefsRepository

    async def execute(self, *args, **kwargs) -> NotificationPrefs:
        prefs = await self.notification_prefs_repository.get(self.user_id)
        if prefs is None:
            return NotificationPrefs(user_id=self.user_id)
        return prefs
