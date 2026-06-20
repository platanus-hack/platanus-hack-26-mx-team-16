from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.application.helpers.pagination import decode_cursor, encode_cursor
from src.common.database.models.usage.process_record import ProcessRecordORM
from src.common.database.models.workspace import WorkflowORM
from src.common.domain.entities.common.pagination import Page
from src.common.infrastructure.helpers.database import atomic_transaction
from src.usage.domain.models.process_record import ProcessRecord
from src.usage.domain.repositories.process_record import ProcessRecordRepository
from src.usage.infrastructure.builders.process_record import build_process_record


class SQLProcessRecordRepository(ProcessRecordRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, record: ProcessRecord) -> ProcessRecord:
        async with atomic_transaction(self.session):
            orm = ProcessRecordORM(
                uuid=record.uuid,
                tenant_id=record.tenant_id,
                workflow_id=record.workflow_id,
                object_key_digest=record.object_key_digest,
                page_count=record.page_count,
                analysis_run_id=record.analysis_run_id,
                processed_at=record.processed_at,
            )
            self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_process_record(orm)

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        limit: int = 25,
        cursor: str | None = None,
    ) -> Page[ProcessRecord]:
        stmt = (
            select(ProcessRecordORM, WorkflowORM.name)
            .outerjoin(WorkflowORM, ProcessRecordORM.workflow_id == WorkflowORM.uuid)
            .where(ProcessRecordORM.tenant_id == tenant_id)
            .order_by(ProcessRecordORM.processed_at.desc(), ProcessRecordORM.uuid.desc())
            .limit(limit + 1)
        )
        if from_dt is not None:
            stmt = stmt.where(ProcessRecordORM.processed_at >= from_dt)
        if to_dt is not None:
            stmt = stmt.where(ProcessRecordORM.processed_at <= to_dt)
        if cursor is not None:
            timestamp, last_uuid = decode_cursor(cursor)
            stmt = stmt.where(
                tuple_(ProcessRecordORM.processed_at, ProcessRecordORM.uuid) <= (timestamp, last_uuid)
            )

        rows = list((await self.session.execute(stmt)).all())

        next_cursor = None
        if len(rows) == limit + 1:
            last_orm, _ = rows.pop()
            next_cursor = encode_cursor(last_orm.processed_at, last_orm.uuid)

        return Page(
            next_cursor=next_cursor,
            items=[build_process_record(orm, workflow_name=name) for orm, name in rows],
            limit=limit,
        )

    async def count_pages_by_tenant(
        self,
        tenant_id: UUID,
        from_dt: datetime,
        to_dt: datetime,
    ) -> int:
        stmt = select(func.coalesce(func.sum(ProcessRecordORM.page_count), 0)).where(
            ProcessRecordORM.tenant_id == tenant_id,
            ProcessRecordORM.processed_at >= from_dt,
            ProcessRecordORM.processed_at <= to_dt,
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())
