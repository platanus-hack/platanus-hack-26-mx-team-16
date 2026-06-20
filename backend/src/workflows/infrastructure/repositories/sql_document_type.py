"""SQLAlchemy implementation of DocumentTypeRepository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.document_type import (
    DocumentTypeORM,
    DocumentTypeVersionORM,
)
from src.common.infrastructure.helpers.database import atomic_transaction
from src.common.domain.models.processing.document_type import (
    DocumentType,
    DocumentTypeVersion,
)
from src.common.domain.exceptions.processing import DocumentTypeNotFoundError
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.infrastructure.builders.document_type import (
    build_document_type,
    build_document_type_version,
)


class SQLDocumentTypeRepository(DocumentTypeRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, document_type_id: UUID, tenant_id: UUID) -> DocumentType | None:
        stmt = select(DocumentTypeORM).where(
            DocumentTypeORM.uuid == document_type_id,
            DocumentTypeORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()
        if orm_instance is None:
            return None
        return build_document_type(orm_instance)

    async def find_by_ids(self, document_type_ids: list[UUID], tenant_id: UUID) -> dict[UUID, str]:
        if not document_type_ids:
            return {}
        stmt = select(DocumentTypeORM.uuid, DocumentTypeORM.name).where(
            DocumentTypeORM.uuid.in_(document_type_ids),
            DocumentTypeORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return {row.uuid: row.name for row in result}

    async def list_by_workflow(self, workflow_id: UUID, tenant_id: UUID) -> list[DocumentType]:
        stmt = (
            select(DocumentTypeORM)
            .where(
                DocumentTypeORM.workflow_id == workflow_id,
                DocumentTypeORM.tenant_id == tenant_id,
            )
            .order_by(DocumentTypeORM.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [build_document_type(orm) for orm in result.scalars()]

    async def list_slugs_by_workflow(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        exclude_document_type_id: UUID | None = None,
    ) -> set[str]:
        stmt = select(DocumentTypeORM.slug).where(
            DocumentTypeORM.workflow_id == workflow_id,
            DocumentTypeORM.tenant_id == tenant_id,
            DocumentTypeORM.slug.is_not(None),
        )
        if exclude_document_type_id is not None:
            stmt = stmt.where(DocumentTypeORM.uuid != exclude_document_type_id)
        result = await self.session.execute(stmt)
        return {slug for slug in result.scalars() if slug}

    async def list_by_tenant(self, tenant_id: UUID) -> list[DocumentType]:
        stmt = (
            select(DocumentTypeORM)
            .where(DocumentTypeORM.tenant_id == tenant_id)
            .order_by(DocumentTypeORM.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [build_document_type(orm) for orm in result.scalars()]

    async def create(self, document_type: DocumentType) -> DocumentType:
        async with atomic_transaction(self.session):
            orm_instance = DocumentTypeORM(
                uuid=document_type.uuid,
                tenant_id=document_type.tenant_id,
                workflow_id=document_type.workflow_id,
                name=document_type.name,
                is_shareable=document_type.is_shareable,
                slug=document_type.slug,
                description=document_type.description,
                fields=document_type.fields,
                keywords=document_type.keywords,
                examples=document_type.examples,
                validation_rules=document_type.validation_rules,
                sample_file_id=document_type.sample_file_id,
                sample_file_text=document_type.sample_file_text,
                current_version=document_type.current_version,
            )
            self.session.add(orm_instance)
            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_document_type(orm_instance)

    async def update(self, document_type: DocumentType) -> DocumentType:
        async with atomic_transaction(self.session):
            stmt = select(DocumentTypeORM).where(
                DocumentTypeORM.uuid == document_type.uuid,
                DocumentTypeORM.tenant_id == document_type.tenant_id,
            )
            result = await self.session.execute(stmt)
            orm_instance = result.scalar_one_or_none()
            if orm_instance is None:
                raise DocumentTypeNotFoundError(str(document_type.uuid))

            orm_instance.name = document_type.name
            orm_instance.description = document_type.description
            orm_instance.is_shareable = document_type.is_shareable
            orm_instance.slug = document_type.slug
            orm_instance.fields = document_type.fields
            orm_instance.keywords = document_type.keywords
            orm_instance.examples = document_type.examples
            orm_instance.validation_rules = document_type.validation_rules
            orm_instance.sample_file_id = document_type.sample_file_id
            orm_instance.sample_file_text = document_type.sample_file_text
            orm_instance.current_version = document_type.current_version
            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_document_type(orm_instance)

    async def delete(self, document_type_id: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            stmt = select(DocumentTypeORM).where(
                DocumentTypeORM.uuid == document_type_id,
                DocumentTypeORM.tenant_id == tenant_id,
            )
            result = await self.session.execute(stmt)
            orm_instance = result.scalar_one_or_none()
            if orm_instance is None:
                raise DocumentTypeNotFoundError(str(document_type_id))

            await self.session.delete(orm_instance)
            await self.session.flush()

    # --- Immutable versions (D6' · pattern: SQLPipelineRepository) ------------

    async def add_version(self, version: DocumentTypeVersion) -> DocumentTypeVersion:
        async with atomic_transaction(self.session):
            orm = DocumentTypeVersionORM(
                uuid=version.uuid,
                document_type_id=version.document_type_id,
                version=version.version,
                fields=version.fields,
                validation_rules=version.validation_rules,
            )
            self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_document_type_version(orm)

    async def get_version(self, document_type_id: UUID, version: int) -> DocumentTypeVersion | None:
        stmt = select(DocumentTypeVersionORM).where(
            DocumentTypeVersionORM.document_type_id == document_type_id,
            DocumentTypeVersionORM.version == version,
        )
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return build_document_type_version(orm) if orm else None

    async def latest_version(self, document_type_id: UUID) -> DocumentTypeVersion | None:
        stmt = (
            select(DocumentTypeVersionORM)
            .where(DocumentTypeVersionORM.document_type_id == document_type_id)
            .order_by(DocumentTypeVersionORM.version.desc())
            .limit(1)
        )
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return build_document_type_version(orm) if orm else None
