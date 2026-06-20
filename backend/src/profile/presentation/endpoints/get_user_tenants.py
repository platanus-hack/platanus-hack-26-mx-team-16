from typing import Annotated

from fastapi import Depends

from src.common.application.queries.tenants import GetUserTenantsQuery
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import (
    AsyncSessionDep,
    BusContextDep,
)
from src.common.infrastructure.dependencies.session import get_authenticated_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.industries.infrastructure.repositories.sql_industry_repository import (
    SQLIndustryRepository,
)


async def get_user_tenants(
    current_user: Annotated[User, Depends(get_authenticated_user)],
    bus_context: BusContextDep,
    session: AsyncSessionDep,
):
    result = await bus_context.query_bus.ask(
        query=GetUserTenantsQuery(user_id=current_user.uuid),
    )

    user_tenants: list[Tenant] = result if isinstance(result, list) else []

    industry_repo = SQLIndustryRepository(session)
    industries_by_tenant = await industry_repo.find_by_tenant_ids([t.uuid for t in user_tenants])

    content = [
        {
            **tenant.model_dump(mode="json"),
            "industries": [industry.model_dump(mode="json") for industry in industries_by_tenant.get(tenant.uuid, [])],
        }
        for tenant in user_tenants
    ]

    return ApiJSONResponse(content=content)
