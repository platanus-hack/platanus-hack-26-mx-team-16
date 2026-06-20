"""SQL implementation of ``NotificationPrefsRepository`` (06-data-model §3.6)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.sites.notification_prefs import NotificationPrefsORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.sites.domain.models.notification_prefs import NotificationPrefs
from src.sites.domain.repositories.notification_prefs import NotificationPrefsRepository
from src.sites.infrastructure.builders.site import build_notification_prefs


@dataclass
class SQLNotificationPrefsRepository(NotificationPrefsRepository):
    session: AsyncSession

    async def get(self, user_id: UUID) -> NotificationPrefs | None:
        orm = await self._find_orm(user_id)
        return build_notification_prefs(orm) if orm else None

    async def upsert(
        self,
        user_id: UUID,
        *,
        email_enabled: bool | None = None,
        slack_webhook_url: str | None = None,
    ) -> NotificationPrefs:
        async with atomic_transaction(self.session):
            orm = await self._find_orm(user_id)
            if orm is None:
                orm = NotificationPrefsORM(user_id=user_id)
                if email_enabled is not None:
                    orm.email_enabled = email_enabled
                orm.slack_webhook_url = slack_webhook_url
                self.session.add(orm)
            else:
                if email_enabled is not None:
                    orm.email_enabled = email_enabled
                if slack_webhook_url is not None:
                    orm.slack_webhook_url = slack_webhook_url
            await self.session.flush()
        return build_notification_prefs(orm)

    async def _find_orm(self, user_id: UUID) -> NotificationPrefsORM | None:
        result = await self.session.execute(
            select(NotificationPrefsORM).where(
                NotificationPrefsORM.user_id == user_id
            )
        )
        return result.scalar_one_or_none()
