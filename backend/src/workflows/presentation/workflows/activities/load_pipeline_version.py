"""Activity: load a sealed, immutable pipeline version (F1).

The interpreter pins ``pipeline_id`` + ``version`` in its input; this activity
materialises the recipe (the ordered ``phases``) from Postgres. Because the
version is immutable append-only, the activity result is stable across replays —
the determinism contract the interpreter relies on.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio import activity
from temporalio.exceptions import ApplicationError

from src.common.application.logging import get_logger
from src.common.domain.entities.workflows.pipeline_run import (
    LoadPipelineVersionInput,
    LoadPipelineVersionOutput,
)
from src.workflows.infrastructure.repositories.sql_pipeline import SQLPipelineRepository

logger = get_logger(__name__)


class LoadPipelineVersionActivity:
    def __init__(self, session_maker: async_sessionmaker) -> None:
        self._session_maker = session_maker

    @activity.defn(name="load_pipeline_version")
    async def load_pipeline_version(self, payload: LoadPipelineVersionInput) -> LoadPipelineVersionOutput:
        data = LoadPipelineVersionInput.model_validate(payload)
        async with self._session_maker() as session:
            repo = SQLPipelineRepository(session=session)
            version = await repo.get_version(data.pipeline_id, data.version)
        if version is None:
            raise ApplicationError(
                f"pipeline version not found: {data.pipeline_id} v{data.version}",
                type="pipeline.version_not_found",
                non_retryable=True,
            )
        return LoadPipelineVersionOutput(
            pipeline_id=version.pipeline_id,
            version=version.version,
            phases=[p.model_dump(mode="json") for p in version.phases],
            output_schema=version.output_schema,
        )
