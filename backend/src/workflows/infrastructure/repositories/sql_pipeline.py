"""SQLAlchemy implementation of PipelineRepository (F1)."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.pipeline import PipelineORM, PipelineVersionORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.workflows.domain.models.pipeline import Pipeline, PipelineVersion
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.infrastructure.builders.pipeline import (
    build_pipeline,
    build_pipeline_version,
)


class SQLPipelineRepository(PipelineRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, pipeline_id: UUID, tenant_id: UUID) -> Pipeline | None:
        stmt = select(PipelineORM).where(
            PipelineORM.uuid == pipeline_id,
            PipelineORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        try:
            return build_pipeline(result.scalar_one())
        except NoResultFound:
            return None

    async def find_by_workflow(self, workflow_id: UUID, tenant_id: UUID) -> Pipeline | None:
        stmt = select(PipelineORM).where(
            PipelineORM.workflow_id == workflow_id,
            PipelineORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        try:
            return build_pipeline(result.scalar_one())
        except NoResultFound:
            return None

    async def upsert(self, pipeline: Pipeline) -> Pipeline:
        async with atomic_transaction(self.session):
            # Identity is the owning workflow (ADR 0002 · UNIQUE(workflow_id)).
            stmt = select(PipelineORM).where(PipelineORM.workflow_id == pipeline.workflow_id)
            existing = (await self.session.execute(stmt)).scalar_one_or_none()
            if existing is None:
                existing = PipelineORM(
                    uuid=pipeline.uuid,
                    workflow_id=pipeline.workflow_id,
                    tenant_id=pipeline.tenant_id,
                    slug=pipeline.slug,
                )
                self.session.add(existing)
            existing.name = pipeline.name
            existing.kind = pipeline.kind.value
            existing.status = pipeline.status.value
            if pipeline.current_version is not None:
                existing.current_version = pipeline.current_version
            await self.session.flush()
            await self.session.refresh(existing)
        return build_pipeline(existing)

    async def add_version(self, version: PipelineVersion) -> PipelineVersion:
        async with atomic_transaction(self.session):
            orm = PipelineVersionORM(
                uuid=version.uuid or uuid4(),
                pipeline_id=version.pipeline_id,
                version=version.version,
                phases=[p.model_dump(mode="json") for p in version.phases],
                output_schema=version.output_schema,
            )
            self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_pipeline_version(orm)

    async def get_version(self, pipeline_id: UUID, version: int) -> PipelineVersion | None:
        stmt = select(PipelineVersionORM).where(
            PipelineVersionORM.pipeline_id == pipeline_id,
            PipelineVersionORM.version == version,
        )
        result = await self.session.execute(stmt)
        try:
            return build_pipeline_version(result.scalar_one())
        except NoResultFound:
            return None

    async def find_version_by_id(self, version_id: UUID) -> PipelineVersion | None:
        stmt = select(PipelineVersionORM).where(PipelineVersionORM.uuid == version_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return build_pipeline_version(orm) if orm else None

    async def latest_version(self, pipeline_id: UUID) -> PipelineVersion | None:
        stmt = (
            select(PipelineVersionORM)
            .where(PipelineVersionORM.pipeline_id == pipeline_id)
            .order_by(PipelineVersionORM.version.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return build_pipeline_version(orm) if orm else None

    async def list_versions(self, pipeline_id: UUID) -> list[PipelineVersion]:
        stmt = (
            select(PipelineVersionORM)
            .where(PipelineVersionORM.pipeline_id == pipeline_id)
            .order_by(PipelineVersionORM.version.desc())
        )
        result = await self.session.execute(stmt)
        return [build_pipeline_version(orm) for orm in result.scalars().all()]
