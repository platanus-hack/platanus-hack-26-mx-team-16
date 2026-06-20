"""SQL implementation of ``AlertRepository`` (06-data-model §3.6)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.scans.alert import AlertORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.scans.domain.models.alert import Alert
from src.scans.domain.repositories.alert import AlertRepository
from src.scans.infrastructure.builders.scan import build_alert


@dataclass
class SQLAlertRepository(AlertRepository):
    session: AsyncSession

    async def log(self, alert: Alert) -> Alert:
        orm = AlertORM(
            uuid=alert.uuid or uuid.uuid4(),
            user_id=alert.user_id,
            site_id=alert.site_id,
            scan_id=alert.scan_id,
            type=alert.type,
            message=alert.message,
            channel=alert.channel,
        )
        async with atomic_transaction(self.session):
            self.session.add(orm)
            await self.session.flush()
        return build_alert(orm)

    async def list_for_user(self, user_id: UUID) -> list[Alert]:
        result = await self.session.execute(
            select(AlertORM)
            .where(AlertORM.user_id == user_id)
            .order_by(AlertORM.sent_at.desc())
        )
        return [build_alert(orm) for orm in result.scalars().all()]
