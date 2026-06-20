"""SQLAlchemy implementation of EvalDatasetRepository (F11 · A5)."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.eval import EvalCaseORM, EvalDatasetORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.evals.domain.models.dataset import EvalCase, EvalDataset
from src.evals.domain.repositories.dataset import EvalDatasetRepository
from src.evals.infrastructure.builders.eval import build_eval_case, build_eval_dataset


class SQLEvalDatasetRepository(EvalDatasetRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, dataset: EvalDataset) -> EvalDataset:
        async with atomic_transaction(self.session):
            orm = EvalDatasetORM(
                uuid=dataset.uuid or uuid4(),
                tenant_id=dataset.tenant_id,
                name=dataset.name,
                pipeline_slug=dataset.pipeline_slug,
            )
            self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_eval_dataset(orm)

    async def list_by_tenant(self, tenant_id: UUID) -> list[EvalDataset]:
        stmt = (
            select(EvalDatasetORM)
            .where(EvalDatasetORM.tenant_id == tenant_id)
            .order_by(EvalDatasetORM.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [build_eval_dataset(orm) for orm in result.scalars().all()]

    async def find_by_id(self, dataset_id: UUID, tenant_id: UUID) -> EvalDataset | None:
        stmt = select(EvalDatasetORM).where(
            EvalDatasetORM.uuid == dataset_id,
            EvalDatasetORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        try:
            return build_eval_dataset(result.scalar_one())
        except NoResultFound:
            return None

    async def add_case(self, case: EvalCase) -> EvalCase:
        async with atomic_transaction(self.session):
            orm = EvalCaseORM(
                uuid=case.uuid or uuid4(),
                tenant_id=case.tenant_id,
                dataset_id=case.dataset_id,
                input_ref=case.input_ref,
                expected=case.expected,
            )
            self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_eval_case(orm)

    async def list_cases(self, dataset_id: UUID, tenant_id: UUID) -> list[EvalCase]:
        stmt = (
            select(EvalCaseORM)
            .where(
                EvalCaseORM.dataset_id == dataset_id,
                EvalCaseORM.tenant_id == tenant_id,
            )
            .order_by(EvalCaseORM.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return [build_eval_case(orm) for orm in result.scalars().all()]
