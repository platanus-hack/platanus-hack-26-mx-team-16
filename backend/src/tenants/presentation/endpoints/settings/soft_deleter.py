from uuid import UUID

from fastapi import Depends, status

from src.common.application.commands.tenants import SoftDeleteTenantCommand
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.tenant_settings import TenantSettingPermission
from src.common.infrastructure.dependencies.common import BusContextDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse


async def soft_delete_tenant(
    tenant_id: UUID,
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    bus_context: BusContextDep = None,
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[TenantSettingPermission.delete])

    await bus_context.command_bus.dispatch(
        SoftDeleteTenantCommand(tenant_id=tenant_id),
        run_async=True,
    )

    return ApiJSONResponse(
        content={"accepted": True},
        status_code=status.HTTP_202_ACCEPTED,
    )
