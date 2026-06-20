"""SQLAlchemy implementation of TenantApiKeyRepository (F9)."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.tenant_api_key import TenantApiKeyORM
from src.common.domain.models.tenant_api_key import TenantApiKey
from src.common.infrastructure.helpers.database import atomic_transaction
from src.tenants.domain.repositories.tenant_api_key import TenantApiKeyRepository
from src.tenants.infrastructure.builders.tenant_api_key import build_tenant_api_key


class SQLTenantApiKeyRepository(TenantApiKeyRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, key: TenantApiKey) -> TenantApiKey:
        async with atomic_transaction(self.session):
            orm = TenantApiKeyORM(
                uuid=key.uuid,
                tenant_id=key.tenant_id,
                name=key.name,
                prefix=key.prefix,
                key_hash=key.key_hash,
                enabled=key.enabled,
                expires_at=key.expires_at,
            )
            self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_tenant_api_key(orm)

    async def find_by_hash(self, key_hash: str) -> TenantApiKey | None:
        orm = (
            await self.session.execute(select(TenantApiKeyORM).where(TenantApiKeyORM.key_hash == key_hash))
        ).scalar_one_or_none()
        return build_tenant_api_key(orm) if orm else None

    async def list_by_tenant(self, tenant_id: UUID) -> list[TenantApiKey]:
        stmt = (
            select(TenantApiKeyORM)
            .where(TenantApiKeyORM.tenant_id == tenant_id)
            .order_by(TenantApiKeyORM.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [build_tenant_api_key(orm) for orm in result.scalars()]

    async def revoke(self, key_id: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            await self.session.execute(
                delete(TenantApiKeyORM).where(
                    TenantApiKeyORM.uuid == key_id,
                    TenantApiKeyORM.tenant_id == tenant_id,
                )
            )
