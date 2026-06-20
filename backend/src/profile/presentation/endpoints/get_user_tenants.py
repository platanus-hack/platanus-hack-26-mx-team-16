from typing import Annotated

from fastapi import Depends

from src.common.application.queries.tenants import GetUserTenantsQuery
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import BusContextDep
from src.common.infrastructure.dependencies.session import get_authenticated_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse


async def get_user_tenants(
    current_user: Annotated[User, Depends(get_authenticated_user)],
    bus_context: BusContextDep,
):
    result = await bus_context.query_bus.ask(
        query=GetUserTenantsQuery(user_id=current_user.uuid),
    )

    user_tenants: list[Tenant] = result if isinstance(result, list) else []

    content = [tenant.model_dump(mode="json") for tenant in user_tenants]

    return ApiJSONResponse(content=content)
