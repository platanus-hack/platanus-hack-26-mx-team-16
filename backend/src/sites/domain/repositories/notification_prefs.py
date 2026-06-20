"""``NotificationPrefsRepository`` ABC (06-data-model §3.6)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.sites.domain.models.notification_prefs import NotificationPrefs


class NotificationPrefsRepository(ABC):
    @abstractmethod
    async def get(self, user_id: UUID) -> NotificationPrefs | None:
        raise NotImplementedError

    @abstractmethod
    async def upsert(
        self,
        user_id: UUID,
        *,
        email_enabled: bool | None = None,
        slack_webhook_url: str | None = None,
    ) -> NotificationPrefs:
        raise NotImplementedError
