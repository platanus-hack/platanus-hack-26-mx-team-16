"""SQLAlchemy implementation of ClassifierRepository (F3, tenant-scoped)."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.classifier import ClassifierORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.workflows.domain.models.classifier import Classifier
from src.workflows.domain.repositories.classifier import ClassifierRepository
from src.workflows.infrastructure.builders.classifier import build_classifier


class SQLClassifierRepository(ClassifierRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_slug(self, slug: str, tenant_id: UUID) -> Classifier | None:
        stmt = select(ClassifierORM).where(
            ClassifierORM.slug == slug,
            ClassifierORM.tenant_id == tenant_id,
        )
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return build_classifier(orm) if orm is not None else None

    async def list_by_tenant(self, tenant_id: UUID) -> list[Classifier]:
        stmt = (
            select(ClassifierORM).where(ClassifierORM.tenant_id == tenant_id).order_by(ClassifierORM.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [build_classifier(orm) for orm in result.scalars()]

    async def upsert(self, classifier: Classifier) -> Classifier:
        async with atomic_transaction(self.session):
            stmt = select(ClassifierORM).where(
                ClassifierORM.tenant_id == classifier.tenant_id,
                ClassifierORM.slug == classifier.slug,
            )
            existing = (await self.session.execute(stmt)).scalar_one_or_none()
            if existing is None:
                existing = ClassifierORM(
                    uuid=classifier.uuid,
                    tenant_id=classifier.tenant_id,
                    slug=classifier.slug,
                )
                self.session.add(existing)
            existing.kind = classifier.kind.value
            existing.config = classifier.config
            existing.enabled = classifier.enabled
        await self.session.refresh(existing)
        return build_classifier(existing)

    async def delete(self, slug: str, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            await self.session.execute(
                delete(ClassifierORM).where(
                    ClassifierORM.slug == slug,
                    ClassifierORM.tenant_id == tenant_id,
                )
            )
