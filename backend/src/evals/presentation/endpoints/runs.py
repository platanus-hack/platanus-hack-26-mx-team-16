"""Eval run endpoints (F11 · A5). JWT-admin.

``create_run`` currently materializes a COMPLETED run with placeholder metrics
(``compute_metrics([], [])``). Once a Temporal activity executes the pipeline
over the dataset, it will feed the real ``cases``/``outputs`` into the same pure
``compute_metrics`` function.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import Depends, status
from pydantic import BaseModel

from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import AsyncSessionDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.evals.application.metrics import compute_metrics
from src.evals.domain.models.run import EvalRun
from src.evals.infrastructure.repositories.sql_run import SQLEvalRunRepository


class CreateRunRequest(BaseModel):
    dataset_id: UUID
    pipeline_version: int | None = None


def _present_run(run: EvalRun) -> dict:
    return {
        "uuid": str(run.uuid),
        "dataset_id": str(run.dataset_id),
        "pipeline_version": run.pipeline_version,
        "status": run.status,
        "metrics": run.metrics,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


async def create_run(
    request: CreateRunRequest,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    run = await SQLEvalRunRepository(session).create(
        EvalRun(
            uuid=uuid4(),
            tenant_id=tenant.uuid,
            dataset_id=request.dataset_id,
            pipeline_version=request.pipeline_version,
            status="COMPLETED",
            metrics=compute_metrics([], []),
        )
    )
    return ApiJSONResponse(content=_present_run(run), status_code=status.HTTP_201_CREATED)


async def get_run(
    id: UUID,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    run = await SQLEvalRunRepository(session).find_by_id(id, tenant.uuid)
    if run is None:
        return ApiJSONResponse(content={"detail": "Eval run not found"}, status_code=status.HTTP_404_NOT_FOUND)
    return ApiJSONResponse(content=_present_run(run), status_code=status.HTTP_200_OK)
