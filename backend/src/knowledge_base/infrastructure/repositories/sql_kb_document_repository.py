"""SQLAlchemy implementation of KBDocumentRepository."""

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.knowledge_base.kb_document import KBDocumentORM
from src.common.database.models.workspace import WorkflowORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.common.domain.models.knowledge_base.kb_document import KBDocument
from src.common.domain.exceptions.knowledge_base import KBDocumentNotFoundError
from src.knowledge_base.domain.repositories.kb_document_repository import KBDocumentRepository
from src.knowledge_base.infrastructure.builders.kb_document_builder import build_kb_document


class SQLKBDocumentRepository(KBDocumentRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, document_id: UUID, tenant_id: UUID) -> KBDocument | None:
        stmt = select(KBDocumentORM).where(
            KBDocumentORM.uuid == document_id,
            KBDocumentORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()
        if orm_instance is None:
            return None
        return build_kb_document(orm_instance)

    async def list_by_tenant(self, tenant_id: UUID) -> list[KBDocument]:
        stmt = (
            select(KBDocumentORM).where(KBDocumentORM.tenant_id == tenant_id).order_by(KBDocumentORM.created_at.desc())
        )
        result = await self.session.execute(stmt)
        orm_instances = list(result.scalars())
        return [build_kb_document(orm) for orm in orm_instances]

    async def list_by_workflow(self, workflow_id: UUID, tenant_id: UUID) -> list[KBDocument]:
        stmt = (
            select(KBDocumentORM)
            .where(KBDocumentORM.workflow_id == workflow_id, KBDocumentORM.tenant_id == tenant_id)
            .order_by(KBDocumentORM.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [build_kb_document(orm) for orm in result.scalars()]

    async def create(self, document: KBDocument) -> KBDocument:
        async with atomic_transaction(self.session):
            orm_instance = KBDocumentORM(
                uuid=document.uuid,
                tenant_id=document.tenant_id,
                file_name=document.file_name,
                slug=document.slug,
                mime=document.mime,
                file_id=document.file_id,
                workflow_id=document.workflow_id,
                extracted_text=document.extracted_text,
                status=document.status.value,
                chunk_count=document.chunk_count,
                error_message=document.error_message,
            )
            self.session.add(orm_instance)
            await self.session.flush()
            await self.session.refresh(orm_instance)

            if document.workflow_id is not None:
                await self._add_document_to_workflow(document.uuid, document.workflow_id, document.tenant_id)

        return build_kb_document(orm_instance)

    async def update(self, document: KBDocument) -> KBDocument:
        async with atomic_transaction(self.session):
            stmt = select(KBDocumentORM).where(
                KBDocumentORM.uuid == document.uuid,
                KBDocumentORM.tenant_id == document.tenant_id,
            )
            result = await self.session.execute(stmt)
            try:
                orm_instance = result.scalar_one()
            except NoResultFound:
                raise KBDocumentNotFoundError(str(document.uuid))

            orm_instance.extracted_text = document.extracted_text
            orm_instance.status = document.status.value
            orm_instance.chunk_count = document.chunk_count
            orm_instance.error_message = document.error_message
            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_kb_document(orm_instance)

    async def delete(self, document_id: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            stmt = select(KBDocumentORM).where(
                KBDocumentORM.uuid == document_id,
                KBDocumentORM.tenant_id == tenant_id,
            )
            result = await self.session.execute(stmt)
            try:
                orm_instance = result.scalar_one()
            except NoResultFound:
                raise KBDocumentNotFoundError(str(document_id))

            if orm_instance.workflow_id is not None:
                await self._remove_document_from_workflow(document_id, orm_instance.workflow_id, tenant_id)

            await self.session.delete(orm_instance)
            await self.session.flush()

    async def find_by_slug_in_workflow(self, workflow_id: UUID, slug: str, tenant_id: UUID) -> KBDocument | None:
        stmt = select(KBDocumentORM).where(
            KBDocumentORM.tenant_id == tenant_id,
            KBDocumentORM.workflow_id == workflow_id,
            KBDocumentORM.slug == slug,
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()
        return build_kb_document(orm_instance) if orm_instance is not None else None

    async def find_by_slug_at_tenant(self, tenant_id: UUID, slug: str) -> KBDocument | None:
        stmt = select(KBDocumentORM).where(
            KBDocumentORM.tenant_id == tenant_id,
            KBDocumentORM.workflow_id.is_(None),
            KBDocumentORM.slug == slug,
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()
        return build_kb_document(orm_instance) if orm_instance is not None else None

    async def resolve_slugs(self, tenant_id: UUID, workflow_id: UUID, slugs: Iterable[str]) -> dict[str, KBDocument]:
        slug_set = {s for s in slugs if s}
        if not slug_set:
            return {}
        stmt = select(KBDocumentORM).where(
            KBDocumentORM.tenant_id == tenant_id,
            KBDocumentORM.slug.in_(slug_set),
            or_(
                KBDocumentORM.workflow_id == workflow_id,
                KBDocumentORM.workflow_id.is_(None),
            ),
        )
        result = await self.session.execute(stmt)
        resolved: dict[str, KBDocument] = {}
        for orm_instance in result.scalars():
            doc = build_kb_document(orm_instance)
            existing = resolved.get(doc.slug)
            # Prefer workflow-scoped over tenant-level for the same slug.
            if existing is None or (existing.workflow_id is None and doc.workflow_id is not None):
                resolved[doc.slug] = doc
        return resolved

    async def _add_document_to_workflow(self, document_id: UUID, workflow_id: UUID, tenant_id: UUID) -> None:
        stmt = select(WorkflowORM).where(
            WorkflowORM.uuid == workflow_id,
            WorkflowORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        workflow_orm = result.scalar_one_or_none()
        if workflow_orm is not None:
            existing_ids: list = list(workflow_orm.kb_document_ids or [])
            doc_str = str(document_id)
            if doc_str not in existing_ids:
                existing_ids.append(doc_str)
                workflow_orm.kb_document_ids = existing_ids
                await self.session.flush()

    async def _remove_document_from_workflow(self, document_id: UUID, workflow_id: UUID, tenant_id: UUID) -> None:
        stmt = select(WorkflowORM).where(
            WorkflowORM.uuid == workflow_id,
            WorkflowORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        workflow_orm = result.scalar_one_or_none()
        if workflow_orm is not None:
            existing_ids: list = list(workflow_orm.kb_document_ids or [])
            doc_str = str(document_id)
            if doc_str in existing_ids:
                existing_ids.remove(doc_str)
                workflow_orm.kb_document_ids = existing_ids
                await self.session.flush()
