"""Eval dataset + case management endpoints (F11 · A5). JWT-admin."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import Depends, status
from pydantic import BaseModel, Field

from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import AsyncSessionDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.evals.domain.models.dataset import EvalCase, EvalDataset
from src.evals.infrastructure.repositories.sql_dataset import SQLEvalDatasetRepository


class CreateDatasetRequest(BaseModel):
    name: str
    pipeline_slug: str


class CreateCaseRequest(BaseModel):
    input_ref: str
    expected: dict = Field(default_factory=dict)


def _present_dataset(dataset: EvalDataset) -> dict:
    return {
        "uuid": str(dataset.uuid),
        "name": dataset.name,
        "pipeline_slug": dataset.pipeline_slug,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
        "updated_at": dataset.updated_at.isoformat() if dataset.updated_at else None,
    }


def _present_case(case: EvalCase) -> dict:
    return {
        "uuid": str(case.uuid),
        "dataset_id": str(case.dataset_id),
        "input_ref": case.input_ref,
        "expected": case.expected,
        "created_at": case.created_at.isoformat() if case.created_at else None,
    }


async def create_dataset(
    request: CreateDatasetRequest,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    dataset = await SQLEvalDatasetRepository(session).create(
        EvalDataset(
            uuid=uuid4(),
            tenant_id=tenant.uuid,
            name=request.name,
            pipeline_slug=request.pipeline_slug,
        )
    )
    return ApiJSONResponse(content=_present_dataset(dataset), status_code=status.HTTP_201_CREATED)


async def list_datasets(
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    datasets = await SQLEvalDatasetRepository(session).list_by_tenant(tenant.uuid)
    return ApiJSONResponse(content=[_present_dataset(d) for d in datasets], status_code=status.HTTP_200_OK)


async def create_case(
    id: UUID,
    request: CreateCaseRequest,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    case = await SQLEvalDatasetRepository(session).add_case(
        EvalCase(
            uuid=uuid4(),
            tenant_id=tenant.uuid,
            dataset_id=id,
            input_ref=request.input_ref,
            expected=request.expected,
        )
    )
    return ApiJSONResponse(content=_present_case(case), status_code=status.HTTP_201_CREATED)
