"""SQLAlchemy implementation of ConnectionAccountRepository."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.connection_account import ConnectionAccountORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.connections.domain.models.connection_account import ConnectionAccount
from src.connections.domain.repositories.connection_account import ConnectionAccountRepository
from src.connections.infrastructure.builders.connection_account import build_connection_account


class SQLConnectionAccountRepository(ConnectionAccountRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, account: ConnectionAccount) -> ConnectionAccount:
        async with atomic_transaction(self.session):
            orm_instance = ConnectionAccountORM(
                uuid=account.uuid,
                tenant_id=account.tenant_id,
                provider=account.provider.value,
                display_name=account.display_name,
                capabilities=[c.value for c in account.capabilities],
                status=account.status.value,
                config=account.config,
                secret=account.secret,
            )
            self.session.add(orm_instance)
            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_connection_account(orm_instance)

    async def update(self, account: ConnectionAccount) -> ConnectionAccount:
        async with atomic_transaction(self.session):
            stmt = select(ConnectionAccountORM).where(
                ConnectionAccountORM.uuid == account.uuid,
                ConnectionAccountORM.tenant_id == account.tenant_id,
            )
            result = await self.session.execute(stmt)
            orm_instance = result.scalar_one()
            orm_instance.display_name = account.display_name
            orm_instance.capabilities = [c.value for c in account.capabilities]
            orm_instance.status = account.status.value
            orm_instance.config = account.config
            if account.secret is not None:
                orm_instance.secret = account.secret
            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_connection_account(orm_instance)

    async def find_by_id(self, account_id: UUID, tenant_id: UUID) -> ConnectionAccount | None:
        stmt = select(ConnectionAccountORM).where(
            ConnectionAccountORM.uuid == account_id,
            ConnectionAccountORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        try:
            orm_instance = result.scalar_one()
        except NoResultFound:
            return None
        return build_connection_account(orm_instance)

    async def list_by_tenant(self, tenant_id: UUID) -> list[ConnectionAccount]:
        stmt = (
            select(ConnectionAccountORM)
            .where(ConnectionAccountORM.tenant_id == tenant_id)
            .order_by(ConnectionAccountORM.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [build_connection_account(orm) for orm in result.scalars().all()]

    async def delete(self, account_id: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            stmt = delete(ConnectionAccountORM).where(
                ConnectionAccountORM.uuid == account_id,
                ConnectionAccountORM.tenant_id == tenant_id,
            )
            await self.session.execute(stmt)
