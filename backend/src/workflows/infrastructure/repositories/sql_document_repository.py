"""SQLAlchemy implementation of DocumentRepository."""

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.processing.file_upload import DocumentORM
from src.common.database.models.workflow_document import WorkflowDocumentORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.exceptions.processing import DocumentNotFoundError
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository
from src.workflows.infrastructure.builders.workflow_document import build_workflow_document


class SQLWorkflowDocumentRepository(WorkflowDocumentRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, document_id: UUID, tenant_id: UUID) -> WorkflowDocument | None:
        stmt = (
            select(WorkflowDocumentORM, DocumentORM.mime.label("file_mime"))
            .outerjoin(DocumentORM, WorkflowDocumentORM.document_id == DocumentORM.uuid)
            .where(
                WorkflowDocumentORM.uuid == document_id,
                WorkflowDocumentORM.tenant_id == tenant_id,
            )
        )
        result = await self.session.execute(stmt)
        orm_instance = result.one_or_none()
        if orm_instance is None:
            return None
        workflow_orm, file_mime = orm_instance
        doc = build_workflow_document(workflow_orm)
        doc.mime_type = file_mime
        return doc

    async def list_by_case(self, case_id: UUID, tenant_id: UUID) -> list[WorkflowDocument]:
        stmt = (
            select(WorkflowDocumentORM)
            .where(
                WorkflowDocumentORM.workflow_case_id == case_id,
                WorkflowDocumentORM.tenant_id == tenant_id,
            )
            .order_by(
                WorkflowDocumentORM.document_type_id.asc().nulls_last(),
                WorkflowDocumentORM.created_at.asc(),
            )
        )
        result = await self.session.execute(stmt)
        orm_instances = list(result.scalars())
        return [build_workflow_document(orm) for orm in orm_instances]

    async def list_by_case_and_file(self, case_id: UUID, file_id: UUID, tenant_id: UUID) -> list[WorkflowDocument]:
        stmt = select(WorkflowDocumentORM).where(
            WorkflowDocumentORM.workflow_case_id == case_id,
            WorkflowDocumentORM.document_id == file_id,
            WorkflowDocumentORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return [build_workflow_document(orm) for orm in result.scalars()]

    async def list_by_processing_job(self, processing_job_id: UUID) -> list[WorkflowDocument]:
        stmt = (
            select(WorkflowDocumentORM)
            .where(WorkflowDocumentORM.processing_job_id == processing_job_id)
            .order_by(WorkflowDocumentORM.document_index.asc())
        )
        result = await self.session.execute(stmt)
        return [build_workflow_document(orm) for orm in result.scalars()]

    async def list_by_processing_job_ids(self, processing_job_ids: list[UUID], tenant_id: UUID) -> list[WorkflowDocument]:
        if not processing_job_ids:
            return []
        stmt = (
            select(WorkflowDocumentORM)
            .where(
                WorkflowDocumentORM.processing_job_id.in_(processing_job_ids),
                WorkflowDocumentORM.tenant_id == tenant_id,
            )
            .order_by(
                WorkflowDocumentORM.processing_job_id,
                WorkflowDocumentORM.document_index.asc().nulls_last(),
            )
        )
        result = await self.session.execute(stmt)
        return [build_workflow_document(orm) for orm in result.scalars()]

    async def list_by_case_ids(self, case_ids: list[UUID], tenant_id: UUID) -> dict[UUID, list[WorkflowDocument]]:
        if not case_ids:
            return {}
        stmt = (
            select(WorkflowDocumentORM)
            .where(
                WorkflowDocumentORM.workflow_case_id.in_(case_ids),
                WorkflowDocumentORM.tenant_id == tenant_id,
            )
            .order_by(
                WorkflowDocumentORM.workflow_case_id,
                WorkflowDocumentORM.document_type_id.asc().nulls_last(),
                WorkflowDocumentORM.created_at.asc(),
            )
        )
        result = await self.session.execute(stmt)
        grouped: dict[UUID, list[WorkflowDocument]] = defaultdict(list)
        for orm in result.scalars():
            if orm.workflow_case_id is not None:
                grouped[orm.workflow_case_id].append(build_workflow_document(orm))
        return grouped

    async def create(self, document: WorkflowDocument) -> WorkflowDocument:
        async with atomic_transaction(self.session):
            orm_instance = WorkflowDocumentORM(
                uuid=document.uuid,
                tenant_id=document.tenant_id,
                workflow_id=document.workflow_id,
                workflow_case_id=document.case_id,
                document_type_id=document.document_type_id,
                name=document.file_name or "document",
                document_id=document.file_id,
                status=document.status,
                source=document.source,
                extraction=document.extraction,
                mapped_extraction=document.mapped_extraction,
                field_confidence=document.field_confidence,
                needs_clarification=document.needs_clarification,
                extraction_pages=document.extraction_pages,
                validation=document.validation,
                extracted_text=document.extracted_text,
                extraction_metadata=document.extraction_metadata,
                # E5 (gotcha): columna nueva ⇒ create() Y update().
                verification=document.verification,
                parent_document_id=document.parent_document_id,
            )
            self.session.add(orm_instance)
            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_workflow_document(orm_instance)

    async def update(self, document: WorkflowDocument) -> WorkflowDocument:
        async with atomic_transaction(self.session):
            stmt = select(WorkflowDocumentORM).where(
                WorkflowDocumentORM.uuid == document.uuid,
                WorkflowDocumentORM.tenant_id == document.tenant_id,
            )
            result = await self.session.execute(stmt)
            try:
                orm_instance = result.scalar_one()
            except NoResultFound:
                raise DocumentNotFoundError(str(document.uuid))

            orm_instance.name = document.file_name or "document"
            orm_instance.document_id = document.file_id
            orm_instance.document_type_id = document.document_type_id
            orm_instance.status = document.status
            orm_instance.source = document.source
            orm_instance.extraction = document.extraction
            orm_instance.mapped_extraction = document.mapped_extraction
            # E5 · el clear de needs_clarification (VerifyDocumentField) y la
            # confianza por campo viajan por update() — entidad COMPLETA.
            orm_instance.field_confidence = document.field_confidence
            orm_instance.needs_clarification = document.needs_clarification
            orm_instance.extraction_pages = document.extraction_pages
            orm_instance.validation = document.validation
            orm_instance.extracted_text = document.extracted_text
            orm_instance.extraction_metadata = document.extraction_metadata
            # E2 · spec case-output: per-document structured output + provenance.
            orm_instance.output = document.output
            orm_instance.output_provenance = document.output_provenance
            # E5 · verificación por campo + lineage del split (gotcha: update
            # persiste la entidad COMPLETA — create() Y update()).
            orm_instance.verification = document.verification
            orm_instance.parent_document_id = document.parent_document_id
            # E5 · fan-out: la reasignación del doc a su child case viaja por
            # update() (CreateChildCases._reassign_document).
            orm_instance.workflow_case_id = document.case_id

            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_workflow_document(orm_instance)

    async def delete(self, document_id: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            stmt = select(WorkflowDocumentORM).where(
                WorkflowDocumentORM.uuid == document_id,
                WorkflowDocumentORM.tenant_id == tenant_id,
            )
            result = await self.session.execute(stmt)
            try:
                orm_instance = result.scalar_one()
            except NoResultFound:
                raise DocumentNotFoundError(str(document_id))

            await self.session.delete(orm_instance)
            await self.session.flush()
