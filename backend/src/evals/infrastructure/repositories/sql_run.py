"""SQLAlchemy implementation of EvalRunRepository (F11 · A5)."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.eval import EvalRunORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.evals.domain.models.run import EvalRun
from src.evals.domain.repositories.run import EvalRunRepository
from src.evals.infrastructure.builders.eval import build_eval_run


class SQLEvalRunRepository(EvalRunRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, run: EvalRun) -> EvalRun:
        async with atomic_transaction(self.session):
            orm = EvalRunORM(
                uuid=run.uuid or uuid4(),
                tenant_id=run.tenant_id,
                dataset_id=run.dataset_id,
                pipeline_version=run.pipeline_version,
                status=run.status,
                metrics=run.metrics,
            )
            self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_eval_run(orm)

    async def find_by_id(self, run_id: UUID, tenant_id: UUID) -> EvalRun | None:
        stmt = select(EvalRunORM).where(
            EvalRunORM.uuid == run_id,
            EvalRunORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        try:
            return build_eval_run(result.scalar_one())
        except NoResultFound:
            return None
