"""SQLAlchemy implementation of StaffAccessEventRepository (ADR 0001).

Append-only por construcción: el repo solo expone ``append`` y ``list``.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.staff_access_event import StaffAccessEventORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.staff.domain.models.staff_access_event import StaffAccessEvent
from src.staff.domain.repositories.staff_access_event import StaffAccessEventRepository
from src.staff.infrastructure.builders.staff_access_event import build_staff_access_event


class SQLStaffAccessEventRepository(StaffAccessEventRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def append(self, event: StaffAccessEvent) -> StaffAccessEvent:
        async with atomic_transaction(self.session):
            orm = StaffAccessEventORM(uuid=event.uuid, **event.persist_dict)
            self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_staff_access_event(orm)

    async def list(
        self,
        staff_user_id: UUID | None = None,
        tenant_id: UUID | None = None,
        action: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StaffAccessEvent]:
        stmt = select(StaffAccessEventORM)
        if staff_user_id is not None:
            stmt = stmt.where(StaffAccessEventORM.staff_user_id == staff_user_id)
        if tenant_id is not None:
            stmt = stmt.where(StaffAccessEventORM.tenant_id == tenant_id)
        if action is not None:
            stmt = stmt.where(StaffAccessEventORM.action == action)
        stmt = stmt.order_by(StaffAccessEventORM.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [build_staff_access_event(orm) for orm in result.scalars()]
