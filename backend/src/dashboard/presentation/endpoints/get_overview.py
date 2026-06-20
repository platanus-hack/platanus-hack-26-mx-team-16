from fastapi import Depends, Query, status

from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.dashboard import DashboardPermission
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.dependencies.tenant import (
    get_required_tenant,
    get_required_tenant_user,
)
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.dashboard.application.use_cases.get_overview import GetOverview
from src.dashboard.presentation.presenters.dashboard import OverviewPresenter


async def get_overview(
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    tenant_user: TenantUser = Depends(get_required_tenant_user),
    throughput_months: int = Query(default=12, ge=1, le=24, alias="throughputMonths"),
    recent_limit: int = Query(default=5, ge=1, le=20, alias="recentLimit"),
) -> ApiJSONResponse:
    check_tenant_permission(tenant_user, permissions=[DashboardPermission.view])
    # `tenant.time_zone` is a `TimeZone` enum (not a string subclass), so
    # we extract the IANA name via `.value` before passing it into the
    # use case which feeds it straight to `ZoneInfo(...)`.
    data = await GetOverview(
        tenant_id=tenant.uuid,
        tenant_time_zone=tenant.time_zone.value if tenant.time_zone else "UTC",
        throughput_months=throughput_months,
        recent_limit=recent_limit,
        dashboard_metrics_repository=app_context.domain.dashboard_metrics_repository,
    ).execute()
    return ApiJSONResponse(
        content=OverviewPresenter(instance=data).to_dict,
        status_code=status.HTTP_200_OK,
    )
