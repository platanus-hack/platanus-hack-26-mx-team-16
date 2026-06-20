"""SQLAlchemy implementation of CaseEventRepository (E4 · append-only)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.case_event import CaseEventORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.workflows.domain.models.case_event import CaseEvent
from src.workflows.domain.repositories.case_event import CaseEventRepository
from src.workflows.infrastructure.builders.case_event import build_case_event


class SQLCaseEventRepository(CaseEventRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, event: CaseEvent) -> CaseEvent:
        # Idempotencia ante retries (la activity puede re-ejecutarse tras un
        # éxito no confirmado): mismo dedupe_key ⇒ devuelve la fila existente.
        if event.dedupe_key is not None:
            existing = await self.session.execute(
                select(CaseEventORM).where(
                    CaseEventORM.tenant_id == event.tenant_id,
                    CaseEventORM.dedupe_key == event.dedupe_key,
                )
            )
            found = existing.scalar_one_or_none()
            if found is not None:
                return build_case_event(found)
        async with atomic_transaction(self.session):
            orm = CaseEventORM(
                uuid=event.uuid,
                tenant_id=event.tenant_id,
                case_id=event.case_id,
                type=event.type,
                payload=event.payload,
                actor=event.actor,
                dedupe_key=event.dedupe_key,
            )
            self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_case_event(orm)

    async def list_by_case(
        self,
        case_id: UUID,
        tenant_id: UUID,
        limit: int = 50,
        desc: bool = True,
    ) -> list[CaseEvent]:
        order = CaseEventORM.created_at.desc() if desc else CaseEventORM.created_at.asc()
        stmt = (
            select(CaseEventORM)
            .where(
                CaseEventORM.case_id == case_id,
                CaseEventORM.tenant_id == tenant_id,
            )
            .order_by(order, CaseEventORM.uuid.desc() if desc else CaseEventORM.uuid.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [build_case_event(orm) for orm in result.scalars().all()]

    async def count_by_type_since(
        self,
        types: list[str],
        since: datetime,
        tenant_id: UUID | None = None,
    ) -> list[tuple[UUID, str, str | None, int]]:
        if not types:
            return []
        stmt = (
            select(
                CaseEventORM.tenant_id,
                CaseEventORM.type,
                CaseEventORM.actor,
                func.count().label("count"),
            )
            .where(
                CaseEventORM.type.in_(types),
                CaseEventORM.created_at >= since,
            )
            .group_by(CaseEventORM.tenant_id, CaseEventORM.type, CaseEventORM.actor)
        )
        if tenant_id is not None:
            stmt = stmt.where(CaseEventORM.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return [(row.tenant_id, row.type, row.actor, row.count) for row in result.all()]
