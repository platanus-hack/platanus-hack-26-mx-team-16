"""SQLAlchemy implementation of CaseRepository."""

from uuid import UUID

from sqlalchemy import exists, func, select, tuple_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.application.helpers.pagination import decode_cursor, encode_cursor
from src.common.database.models.processing.workflow_case import WorkflowCaseORM
from src.common.database.models.workflow_document import WorkflowDocumentORM
from src.common.database.models.workflow_processing_job import WorkflowProcessingJobORM
from src.common.domain.entities.common.pagination import Page
from src.common.domain.enums.workflows import WorkflowProcessingJobStatus
from src.common.infrastructure.helpers.database import atomic_transaction
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.common.domain.exceptions.processing import CaseNotFoundError
from src.workflows.domain.filters.workflow_case import WorkflowCaseFilters
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.infrastructure.builders.workflow_case import build_workflow_case


class SQLWorkflowCaseRepository(WorkflowCaseRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, case_id: UUID, tenant_id: UUID) -> WorkflowCase | None:
        stmt = select(WorkflowCaseORM).where(
            WorkflowCaseORM.uuid == case_id,
            WorkflowCaseORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()
        if orm_instance is None:
            return None
        return build_workflow_case(orm_instance)

    async def find_by_external_ref(
        self, workflow_id: UUID, external_ref: str, tenant_id: UUID
    ) -> WorkflowCase | None:
        stmt = select(WorkflowCaseORM).where(
            WorkflowCaseORM.workflow_id == workflow_id,
            WorkflowCaseORM.external_ref == external_ref,
            WorkflowCaseORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()
        if orm_instance is None:
            return None
        return build_workflow_case(orm_instance)

    async def list_by_workflow(self, workflow_id: UUID, tenant_id: UUID) -> list[WorkflowCase]:
        stmt = (
            select(WorkflowCaseORM)
            .where(
                WorkflowCaseORM.workflow_id == workflow_id,
                WorkflowCaseORM.tenant_id == tenant_id,
            )
            .order_by(WorkflowCaseORM.created_at.desc())
        )
        result = await self.session.execute(stmt)
        orm_instances = list(result.scalars())
        return [build_workflow_case(orm) for orm in orm_instances]

    async def list_children(self, parent_case_id: UUID, tenant_id: UUID) -> list[WorkflowCase]:
        stmt = (
            select(WorkflowCaseORM)
            .where(
                WorkflowCaseORM.parent_case_id == parent_case_id,
                WorkflowCaseORM.tenant_id == tenant_id,
            )
            .order_by(WorkflowCaseORM.created_at.asc(), WorkflowCaseORM.uuid.asc())
        )
        result = await self.session.execute(stmt)
        return [build_workflow_case(orm) for orm in result.scalars()]

    async def count_children_by_status(
        self, parent_case_id: UUID, tenant_id: UUID
    ) -> dict[str, int]:
        stmt = (
            select(WorkflowCaseORM.status, func.count(WorkflowCaseORM.uuid))
            .where(
                WorkflowCaseORM.parent_case_id == parent_case_id,
                WorkflowCaseORM.tenant_id == tenant_id,
            )
            .group_by(WorkflowCaseORM.status)
        )
        result = await self.session.execute(stmt)
        return {status: count for status, count in result.all()}

    async def filter_paginated(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        filters: WorkflowCaseFilters,
    ) -> Page[WorkflowCase]:
        stmt = self._build_filter_query(workflow_id, tenant_id, filters, paginated=True)
        result = await self.session.execute(stmt)
        orm_instances = list(result.scalars())

        next_cursor = None
        if len(orm_instances) == filters.limit + 1:
            last = orm_instances.pop()
            next_cursor = encode_cursor(last.created_at, last.uuid)

        return Page(
            next_cursor=next_cursor,
            items=[build_workflow_case(orm) for orm in orm_instances],
            limit=filters.limit,
        )

    @staticmethod
    def _build_filter_query(
        workflow_id: UUID,
        tenant_id: UUID,
        filters: WorkflowCaseFilters,
        paginated: bool = False,
    ):
        stmt = (
            select(WorkflowCaseORM)
            .where(
                WorkflowCaseORM.workflow_id == workflow_id,
                WorkflowCaseORM.tenant_id == tenant_id,
            )
            .order_by(WorkflowCaseORM.created_at.desc(), WorkflowCaseORM.uuid.desc())
        )

        if paginated:
            stmt = stmt.limit(filters.limit + 1)

        if filters.enum_statuses:
            stmt = stmt.where(WorkflowCaseORM.status.in_([str(status) for status in filters.enum_statuses]))

        if filters.search:
            stmt = stmt.where(WorkflowCaseORM.name.ilike(f"%{filters.search}%"))

        if filters.with_failed_runs:
            # Filtro «Con errores»: casos con al menos un run FAILED.
            stmt = stmt.where(
                exists().where(
                    WorkflowProcessingJobORM.workflow_case_id == WorkflowCaseORM.uuid,
                    WorkflowProcessingJobORM.status == WorkflowProcessingJobStatus.FAILED.value,
                )
            )

        # E5 · fan-out: panel children del padre (filtro parentCaseId).
        if filters.parent_case_uuid:
            stmt = stmt.where(WorkflowCaseORM.parent_case_id == filters.parent_case_uuid)

        if filters.doctype_uuids:
            stmt = stmt.where(
                exists(
                    select(WorkflowDocumentORM.uuid).where(
                        WorkflowDocumentORM.document_type_id.in_(filters.doctype_uuids),
                        exists(
                            select(WorkflowProcessingJobORM.uuid).where(
                                WorkflowProcessingJobORM.uuid == WorkflowDocumentORM.processing_job_id,
                                WorkflowProcessingJobORM.workflow_case_id == WorkflowCaseORM.uuid,
                            )
                        ),
                    )
                )
            )

        if filters.parsed_date_from:
            stmt = stmt.where(WorkflowCaseORM.created_at >= filters.parsed_date_from)

        if filters.parsed_date_to:
            stmt = stmt.where(WorkflowCaseORM.created_at <= filters.parsed_date_to)

        if filters.cursor:
            timestamp, last_uuid = decode_cursor(filters.cursor)
            stmt = stmt.where(tuple_(WorkflowCaseORM.created_at, WorkflowCaseORM.uuid) <= (timestamp, last_uuid))

        return stmt

    async def create(self, case: WorkflowCase) -> WorkflowCase:
        async with atomic_transaction(self.session):
            orm_instance = WorkflowCaseORM(
                uuid=case.uuid,
                tenant_id=case.tenant_id,
                workflow_id=case.workflow_id,
                name=case.name,
                status=case.status,
                last_ocr_provider=case.last_ocr_provider,
                external_ref=case.external_ref,
                pipeline_id=case.pipeline_id,
                # E4 (gotcha E3 external_ref): columna nueva ⇒ create() Y update().
                pipeline_version_id=case.pipeline_version_id,
                # E5 · fan-out: lineage padre→children.
                parent_case_id=case.parent_case_id,
                ready_at=case.ready_at,
                completeness=case.completeness,
                created_by=case.created_by,
            )
            self.session.add(orm_instance)
            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_workflow_case(orm_instance)

    async def update(self, case: WorkflowCase) -> WorkflowCase:
        async with atomic_transaction(self.session):
            stmt = select(WorkflowCaseORM).where(
                WorkflowCaseORM.uuid == case.uuid,
                WorkflowCaseORM.tenant_id == case.tenant_id,
            )
            result = await self.session.execute(stmt)
            try:
                orm_instance = result.scalar_one()
            except NoResultFound:
                raise CaseNotFoundError(str(case.uuid))

            orm_instance.name = case.name
            orm_instance.status = case.status
            orm_instance.last_ocr_provider = case.last_ocr_provider
            # E4 (gotcha E3 external_ref): columna nueva ⇒ create() Y update().
            # update() persiste la entidad COMPLETA — la inmutabilidad de un
            # campo se decide en el use case, nunca soltándolo aquí en silencio.
            orm_instance.external_ref = case.external_ref
            orm_instance.pipeline_id = case.pipeline_id
            orm_instance.pipeline_version_id = case.pipeline_version_id
            orm_instance.parent_case_id = case.parent_case_id
            orm_instance.ready_at = case.ready_at
            orm_instance.completeness = case.completeness

            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_workflow_case(orm_instance)

    async def delete(self, case_id: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            stmt = select(WorkflowCaseORM).where(
                WorkflowCaseORM.uuid == case_id,
                WorkflowCaseORM.tenant_id == tenant_id,
            )
            result = await self.session.execute(stmt)
            try:
                orm_instance = result.scalar_one()
            except NoResultFound:
                raise CaseNotFoundError(str(case_id))

            await self.session.delete(orm_instance)
            await self.session.flush()
