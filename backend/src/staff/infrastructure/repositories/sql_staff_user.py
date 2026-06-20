"""SQLAlchemy implementation of StaffUserRepository (ADR 0001)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.staff_user import StaffUserORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.staff.domain.models.staff_user import StaffUser, StaffUserStatus
from src.staff.domain.repositories.staff_user import StaffUserRepository
from src.staff.infrastructure.builders.staff_user import build_staff_user


class SQLStaffUserRepository(StaffUserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_active_by_user_id(self, user_id: UUID) -> StaffUser | None:
        orm = (
            await self.session.execute(
                select(StaffUserORM).where(
                    StaffUserORM.user_id == user_id,
                    StaffUserORM.status == StaffUserStatus.ACTIVE.value,
                )
            )
        ).scalar_one_or_none()
        return build_staff_user(orm) if orm else None

    async def find_by_user_id(self, user_id: UUID) -> StaffUser | None:
        orm = (
            await self.session.execute(select(StaffUserORM).where(StaffUserORM.user_id == user_id))
        ).scalar_one_or_none()
        return build_staff_user(orm) if orm else None

    async def find_by_id(self, staff_user_id: UUID) -> StaffUser | None:
        orm = (
            await self.session.execute(select(StaffUserORM).where(StaffUserORM.uuid == staff_user_id))
        ).scalar_one_or_none()
        return build_staff_user(orm) if orm else None

    async def add(self, staff_user: StaffUser) -> StaffUser:
        async with atomic_transaction(self.session):
            orm = StaffUserORM(uuid=staff_user.uuid, **staff_user.persist_dict)
            self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_staff_user(orm)

    async def update(self, staff_user: StaffUser) -> StaffUser:
        async with atomic_transaction(self.session):
            orm = (
                await self.session.execute(
                    select(StaffUserORM).where(StaffUserORM.uuid == staff_user.uuid)
                )
            ).scalar_one()
            # Entidad COMPLETA (gotcha update): rol, status y revoked_at.
            for key, value in staff_user.persist_dict.items():
                setattr(orm, key, value)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_staff_user(orm)
