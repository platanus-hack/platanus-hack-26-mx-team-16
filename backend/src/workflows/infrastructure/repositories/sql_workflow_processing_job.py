from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete as sa_delete, exists, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.common.application.helpers.pagination import decode_cursor, encode_cursor
from src.common.database.models.processing.file_upload import DocumentORM
from src.common.database.models.workflow_document import WorkflowDocumentORM
from src.common.database.models.workflow_processing_job import WorkflowProcessingJobORM
from src.common.domain.entities.common.pagination import Page
from src.common.domain.enums.workflows import (
    WorkflowProcessingJobStatus,
    WorkflowProcessingJobTrigger,
)
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.common.infrastructure.helpers.database import atomic_transaction
from src.workflows.domain.filters.workflow_processing_job import WorkflowProcessingJobFilters
from src.workflows.domain.repositories.workflow_processing_job_repository import (
    WorkflowProcessingJobRepository,
)


_TERMINAL_STATUSES = [s.value for s in WorkflowProcessingJobStatus if s.is_terminal]


class SQLWorkflowProcessingJobRepository(WorkflowProcessingJobRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, processing_job: WorkflowProcessingJob) -> WorkflowProcessingJob:
        orm = WorkflowProcessingJobORM(
            uuid=processing_job.uuid,
            temporal_workflow_id=processing_job.temporal_workflow_id,
            tenant_id=processing_job.tenant_id,
            workflow_id=processing_job.workflow_id,
            workflow_case_id=processing_job.workflow_case_id,
            file_id=processing_job.file_id,
            status=processing_job.status.value,
            attempts=processing_job.attempts,
            error=processing_job.error,
            result_summary=processing_job.result_summary,
            created_by_id=processing_job.created_by_id,
            trigger=processing_job.trigger.value,
        )
        self.session.add(orm)
        await self.session.flush()
        await self.session.refresh(orm)
        return WorkflowProcessingJob.model_validate(orm)

    async def find_by_uuid(self, uuid: UUID) -> WorkflowProcessingJob | None:
        stmt = select(WorkflowProcessingJobORM).where(WorkflowProcessingJobORM.uuid == uuid)
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        return WorkflowProcessingJob.model_validate(row) if row is not None else None

    async def find_by_temporal_workflow_id(self, temporal_workflow_id: str) -> WorkflowProcessingJob | None:
        stmt = select(WorkflowProcessingJobORM).where(WorkflowProcessingJobORM.temporal_workflow_id == temporal_workflow_id)
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        return WorkflowProcessingJob.model_validate(row) if row is not None else None

    async def filter_paginated(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        filters: WorkflowProcessingJobFilters,
    ) -> Page[WorkflowProcessingJob]:
        stmt = self._build_filter_query(workflow_id, tenant_id, filters, paginated=True).options(
            selectinload(WorkflowProcessingJobORM.file)
        )
        rows = list((await self.session.execute(stmt)).scalars().all())

        next_cursor = None
        if len(rows) == filters.limit + 1:
            last = rows.pop()
            next_cursor = encode_cursor(last.created_at, last.uuid)

        return Page(
            next_cursor=next_cursor,
            items=[self._to_domain(row) for row in rows],
            limit=filters.limit,
        )

    @staticmethod
    def _to_domain(row: WorkflowProcessingJobORM) -> WorkflowProcessingJob:
        domain = WorkflowProcessingJob.model_validate(row)
        domain.file_name = row.file.file_name if row.file is not None else None
        return domain

    @staticmethod
    def _build_filter_query(
        workflow_id: UUID,
        tenant_id: UUID,
        filters: WorkflowProcessingJobFilters,
        paginated: bool = False,
    ):
        stmt = (
            select(WorkflowProcessingJobORM)
            .where(
                WorkflowProcessingJobORM.workflow_id == workflow_id,
                WorkflowProcessingJobORM.tenant_id == tenant_id,
            )
            .order_by(WorkflowProcessingJobORM.created_at.desc(), WorkflowProcessingJobORM.uuid.desc())
        )

        if paginated:
            stmt = stmt.limit(filters.limit + 1)

        if filters.workflow_case_id:
            stmt = stmt.where(WorkflowProcessingJobORM.workflow_case_id == filters.workflow_case_id)

        if filters.enum_statuses:
            stmt = stmt.where(WorkflowProcessingJobORM.status.in_([status.value for status in filters.enum_statuses]))

        if filters.search:
            # JOIN opcional: sólo se añade cuando hay término de búsqueda
            stmt = stmt.join(DocumentORM, WorkflowProcessingJobORM.file_id == DocumentORM.uuid, isouter=True).where(
                DocumentORM.file_name.ilike(f"%{filters.search}%")
            )

        if filters.doctype_uuids:
            stmt = stmt.where(
                exists(
                    select(WorkflowDocumentORM.uuid).where(
                        WorkflowDocumentORM.processing_job_id == WorkflowProcessingJobORM.uuid,
                        WorkflowDocumentORM.document_type_id.in_(filters.doctype_uuids),
                    )
                )
            )

        if filters.parsed_date_from:
            stmt = stmt.where(WorkflowProcessingJobORM.created_at >= filters.parsed_date_from)

        if filters.parsed_date_to:
            stmt = stmt.where(WorkflowProcessingJobORM.created_at <= filters.parsed_date_to)

        if filters.cursor:
            timestamp, last_uuid = decode_cursor(filters.cursor)
            stmt = stmt.where(
                tuple_(WorkflowProcessingJobORM.created_at, WorkflowProcessingJobORM.uuid) <= (timestamp, last_uuid)
            )

        return stmt

    async def claim(self, uuid: UUID) -> WorkflowProcessingJob | None:
        stmt = (
            select(WorkflowProcessingJobORM)
            .where(
                WorkflowProcessingJobORM.uuid == uuid,
                WorkflowProcessingJobORM.status.in_(
                    [
                        WorkflowProcessingJobStatus.PENDING.value,
                        WorkflowProcessingJobStatus.RUNNING.value,
                    ]
                ),
            )
            .with_for_update(skip_locked=True)
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        row.status = WorkflowProcessingJobStatus.RUNNING.value
        row.attempts += 1
        # Record the wall-clock start of the run only on the FIRST claim, so
        # retries that re-claim a row don't reset the timing baseline.
        if row.started_at is None:
            row.started_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(row)
        return WorkflowProcessingJob.model_validate(row)

    async def mark_done(self, uuid: UUID, summary: dict | None) -> None:
        # Atomic guard: never overwrite a row already in a terminal state.
        await self.session.execute(
            update(WorkflowProcessingJobORM)
            .where(
                WorkflowProcessingJobORM.uuid == uuid,
                WorkflowProcessingJobORM.status.notin_(_TERMINAL_STATUSES),
            )
            .values(
                status=WorkflowProcessingJobStatus.COMPLETED.value,
                error=None,
                result_summary=summary,
                finished_at=datetime.now(UTC),
            )
        )
        await self.session.flush()

    async def mark_failed(self, uuid: UUID, error: str) -> None:
        # Atomic guard: never flip a successfully-completed row to FAILED.
        await self.session.execute(
            update(WorkflowProcessingJobORM)
            .where(
                WorkflowProcessingJobORM.uuid == uuid,
                WorkflowProcessingJobORM.status.notin_(_TERMINAL_STATUSES),
            )
            .values(
                status=WorkflowProcessingJobStatus.FAILED.value,
                error=error,
                finished_at=datetime.now(UTC),
            )
        )
        await self.session.flush()

    async def reset_to_pending(
        self,
        uuid: UUID,
        trigger: WorkflowProcessingJobTrigger | None = None,
    ) -> None:
        stmt = select(WorkflowProcessingJobORM).where(WorkflowProcessingJobORM.uuid == uuid)
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return
        row.status = WorkflowProcessingJobStatus.PENDING.value
        row.error = None
        # Reset timing so the next claim() captures fresh started_at.
        row.started_at = None
        row.finished_at = None
        if trigger is not None:
            row.trigger = trigger.value
        await self.session.flush()

    async def list_unfinished(self) -> list[WorkflowProcessingJob]:
        stmt = select(WorkflowProcessingJobORM).where(
            WorkflowProcessingJobORM.status.in_(
                [
                    WorkflowProcessingJobStatus.PENDING.value,
                    WorkflowProcessingJobStatus.RUNNING.value,
                    WorkflowProcessingJobStatus.PROCESSING.value,
                ]
            )
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [WorkflowProcessingJob.model_validate(row) for row in rows]

    async def failed_case_ids(self, case_ids: list[UUID], tenant_id: UUID) -> set[UUID]:
        if not case_ids:
            return set()
        stmt = (
            select(WorkflowProcessingJobORM.workflow_case_id)
            .where(
                WorkflowProcessingJobORM.workflow_case_id.in_(case_ids),
                WorkflowProcessingJobORM.tenant_id == tenant_id,
                WorkflowProcessingJobORM.status == WorkflowProcessingJobStatus.FAILED.value,
            )
            .distinct()
        )
        result = await self.session.execute(stmt)
        return {case_id for (case_id,) in result if case_id is not None}

    async def list_by_workflow(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        workflow_case_id: UUID | None = None,
    ) -> list[WorkflowProcessingJob]:
        stmt = select(WorkflowProcessingJobORM).where(
            WorkflowProcessingJobORM.workflow_id == workflow_id,
            WorkflowProcessingJobORM.tenant_id == tenant_id,
        )
        if workflow_case_id is not None:
            stmt = stmt.where(WorkflowProcessingJobORM.workflow_case_id == workflow_case_id)
        stmt = stmt.order_by(WorkflowProcessingJobORM.created_at.desc())
        rows = (await self.session.execute(stmt)).scalars().all()
        return [WorkflowProcessingJob.model_validate(row) for row in rows]

    async def list_by_source_token(
        self,
        route_token: str,
        tenant_id: UUID,
        *,
        limit: int = 200,
    ) -> list[WorkflowProcessingJob]:
        # Jobs opened by the public ingest endpoint carry the id
        # `SRC#{route_token}_FILE#…` (connections/.../ingest.py). There is no
        # source_id FK on the job, so we match that immutable prefix. The token
        # is url-safe and may contain LIKE metacharacters, so escape them.
        stmt = (
            select(WorkflowProcessingJobORM)
            .where(
                WorkflowProcessingJobORM.tenant_id == tenant_id,
                WorkflowProcessingJobORM.temporal_workflow_id.startswith(
                    f"SRC#{route_token}_FILE#", autoescape=True
                ),
            )
            .order_by(
                WorkflowProcessingJobORM.created_at.desc(),
                WorkflowProcessingJobORM.uuid.desc(),
            )
            .limit(limit)
            .options(selectinload(WorkflowProcessingJobORM.file))
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(row) for row in rows]

    async def delete(self, uuid: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            await self.session.execute(
                sa_delete(WorkflowProcessingJobORM).where(
                    WorkflowProcessingJobORM.uuid == uuid,
                    WorkflowProcessingJobORM.tenant_id == tenant_id,
                )
            )
            await self.session.flush()

    async def list_for_replay(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        since_seq: int = 0,
        workflow_case_id: UUID | None = None,
    ) -> list[WorkflowProcessingJob]:
        stmt = select(WorkflowProcessingJobORM).where(
            WorkflowProcessingJobORM.workflow_id == workflow_id,
            WorkflowProcessingJobORM.tenant_id == tenant_id,
            WorkflowProcessingJobORM.last_seq > since_seq,
        )
        if workflow_case_id is not None:
            stmt = stmt.where(WorkflowProcessingJobORM.workflow_case_id == workflow_case_id)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [WorkflowProcessingJob.model_validate(row) for row in rows]
