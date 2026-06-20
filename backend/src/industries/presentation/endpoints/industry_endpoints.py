"""Industry CRUD endpoints."""

from uuid import UUID

from fastapi import Depends, status

from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import AsyncSessionDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.industries.application.use_cases.create_industry import CreateIndustry
from src.industries.application.use_cases.delete_industry import DeleteIndustry
from src.industries.application.use_cases.list_industries import ListIndustries
from src.industries.application.use_cases.update_industry import UpdateIndustry
from src.industries.infrastructure.repositories.sql_industry_repository import SQLIndustryRepository
from src.industries.presentation.presenters.industry_presenter import IndustryPresenter
from src.industries.presentation.schemas.industry_schemas import (
    CreateIndustryRequest,
    UpdateIndustryRequest,
)


async def list_industries(
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    industries = await ListIndustries(
        industry_repository=SQLIndustryRepository(session),
    ).execute()
    return ApiJSONResponse(
        content=[IndustryPresenter(instance=i).to_dict for i in industries],
        status_code=status.HTTP_200_OK,
    )


async def create_industry(
    request: CreateIndustryRequest,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    industry = await CreateIndustry(
        slug=request.slug,
        name=request.name,
        icon=request.icon,
        description=request.description,
        industry_repository=SQLIndustryRepository(session),
    ).execute()
    return ApiJSONResponse(
        content=IndustryPresenter(instance=industry).to_dict,
        status_code=status.HTTP_201_CREATED,
    )


async def update_industry(
    industry_id: UUID,
    request: UpdateIndustryRequest,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    industry = await UpdateIndustry(
        industry_id=industry_id,
        industry_repository=SQLIndustryRepository(session),
        name=request.name,
        new_slug=request.slug,
        icon=request.icon,
        description=request.description,
    ).execute()
    return ApiJSONResponse(
        content=IndustryPresenter(instance=industry).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def delete_industry(
    industry_id: UUID,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    await DeleteIndustry(
        industry_id=industry_id,
        industry_repository=SQLIndustryRepository(session),
    ).execute()
    return ApiJSONResponse(
        content={"status": "deleted"},
        status_code=status.HTTP_200_OK,
    )
