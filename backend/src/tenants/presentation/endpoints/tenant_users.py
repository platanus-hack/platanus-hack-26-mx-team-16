from fastapi import Depends, status

from src.common.domain.contexts.domain import DomainContext
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.filters.tenants.tenant_user import TenantUserFilters
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.tenant_user import TenantUserPermission
from src.common.infrastructure.dependencies.common import get_domain_context
from src.common.infrastructure.dependencies.tenant import get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.tenants.presentation.presenters.tenant_user import TenantUserPresenter
from src.users.application.use_cases.tenant_user.lister import TenantUserLister


async def get_tenant_users(
    domain_context: DomainContext = Depends(get_domain_context),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    filters: TenantUserFilters = Depends(),
):
    check_tenant_permission(current_tenant_user, permissions=[TenantUserPermission.view])

    filters.tenant_ids = [current_tenant_user.tenant_id]
    filters.exclude_ids = [current_tenant_user.uuid]
    current_page = await TenantUserLister(
        filters=filters,
        user_repository=domain_context.tenant_user_repository,
    ).execute()

    current_page.apply_presenter(TenantUserPresenter)
    return ApiJSONResponse(
        content=current_page,
        status_code=status.HTTP_200_OK,
    )
