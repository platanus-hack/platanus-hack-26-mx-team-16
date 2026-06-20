from fastapi import Depends, status

from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.entities.tenants.tenant_user_stats import TenantUserStats
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.tenant_user import TenantUserPermission
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.dependencies.tenant import get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.tenants.application.use_cases.user.stats_getter import TenantUserStatsGetter


async def get_tenant_user_stats(
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    app_context: AppContext = Depends(get_app_context),
):
    check_tenant_permission(current_tenant_user, permissions=[TenantUserPermission.view])

    user_stats: TenantUserStats = await TenantUserStatsGetter(
        tenant_id=current_tenant_user.tenant.uuid,
        tenant_user_repository=app_context.domain.tenant_user_repository,
        excluded_tenant_user_ids=[current_tenant_user.uuid],
    ).execute()

    return ApiJSONResponse(
        content=user_stats.model_dump(),
        status_code=status.HTTP_200_OK,
    )
