from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.tenants.tenant_user_invitation import (
    TenantUserInvitationORM,
)
from src.common.domain.enums.tenants import TenantUserInvitationStatus
from src.common.domain.models.tenants.tenant_user_invitation import (
    TenantUserInvitation,
)
from src.common.infrastructure.builders.tenant_user_invitation import (
    build_tenant_user_invitation,
)
from src.common.infrastructure.helpers.database import atomic_transaction
from src.tenants.domain.repositories.tenant_user_invitation import (
    TenantUserInvitationRepository,
)


@dataclass
class SQLTenantUserInvitationRepository(TenantUserInvitationRepository):
    session: AsyncSession

    async def persist(self, invitation: TenantUserInvitation) -> TenantUserInvitation:
        async with atomic_transaction(self.session):
            orm = TenantUserInvitationORM(**invitation.persist_data)
            self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_tenant_user_invitation(orm)

    async def persist_many(self, invitations: list[TenantUserInvitation]) -> list[TenantUserInvitation]:
        if not invitations:
            return []
        async with atomic_transaction(self.session):
            orms = [TenantUserInvitationORM(**inv.persist_data) for inv in invitations]
            self.session.add_all(orms)
            await self.session.flush()
            for orm in orms:
                await self.session.refresh(orm)
        return [build_tenant_user_invitation(orm) for orm in orms]

    async def find_by_token(self, token: str) -> TenantUserInvitation | None:
        stmt = select(TenantUserInvitationORM).where(TenantUserInvitationORM.token == token)
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return build_tenant_user_invitation(orm) if orm else None

    async def find_by_id(self, invitation_id: UUID) -> TenantUserInvitation | None:
        stmt = select(TenantUserInvitationORM).where(TenantUserInvitationORM.uuid == invitation_id)
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return build_tenant_user_invitation(orm) if orm else None

    async def list_pending_by_tenant(self, tenant_id: UUID) -> list[TenantUserInvitation]:
        stmt = (
            select(TenantUserInvitationORM)
            .where(TenantUserInvitationORM.tenant_id == tenant_id)
            .where(TenantUserInvitationORM.status == TenantUserInvitationStatus.PENDING.value)
            .order_by(TenantUserInvitationORM.created_at.desc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [build_tenant_user_invitation(o) for o in rows]

    async def mark_accepted(self, invitation_id: UUID) -> TenantUserInvitation:
        async with atomic_transaction(self.session):
            await self.session.execute(
                update(TenantUserInvitationORM)
                .where(TenantUserInvitationORM.uuid == invitation_id)
                .values(
                    status=TenantUserInvitationStatus.ACCEPTED.value,
                    accepted_at=datetime.now(UTC),
                )
            )
        updated = await self.find_by_id(invitation_id)
        assert updated is not None
        return updated

    async def mark_expired(self, invitation_id: UUID) -> TenantUserInvitation:
        async with atomic_transaction(self.session):
            await self.session.execute(
                update(TenantUserInvitationORM)
                .where(TenantUserInvitationORM.uuid == invitation_id)
                .values(status=TenantUserInvitationStatus.EXPIRED.value)
            )
        updated = await self.find_by_id(invitation_id)
        assert updated is not None
        return updated

    async def rotate_token(self, invitation_id: UUID, new_token: str) -> TenantUserInvitation:
        async with atomic_transaction(self.session):
            await self.session.execute(
                update(TenantUserInvitationORM)
                .where(TenantUserInvitationORM.uuid == invitation_id)
                .values(token=new_token)
            )
        updated = await self.find_by_id(invitation_id)
        assert updated is not None
        return updated
